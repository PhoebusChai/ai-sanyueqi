"""系统工具 - 时间、应用、延时任务"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime
import platform
import subprocess
import os
import glob
import threading
import uuid

router = APIRouter(prefix="/system", tags=["系统"])

# 存储定时任务
scheduled_tasks = {}


class OpenAppRequest(BaseModel):
    app_name: str


class DelayedTaskRequest(BaseModel):
    action: str
    delay_seconds: int
    params: dict = {}


def find_application(app_name: str) -> str | None:
    """智能查找应用程序路径"""
    app_lower = app_name.lower()
    
    # 系统内置应用
    system_apps = {
        "notepad": "notepad.exe", "记事本": "notepad.exe",
        "calculator": "calc.exe", "计算器": "calc.exe",
        "explorer": "explorer.exe", "资源管理器": "explorer.exe",
        "cmd": "cmd.exe", "命令提示符": "cmd.exe",
        "powershell": "powershell.exe",
        "paint": "mspaint.exe", "画图": "mspaint.exe",
        "snipping": "snippingtool.exe", "截图": "snippingtool.exe",
    }
    if app_lower in system_apps:
        return system_apps[app_lower]
    
    # 搜索路径
    search_paths = [
        os.path.expandvars(r"%ProgramFiles%"),
        os.path.expandvars(r"%ProgramFiles(x86)%"),
        os.path.expandvars(r"%LocalAppData%"),
        os.path.expandvars(r"%AppData%"),
        os.path.expandvars(r"%UserProfile%\Desktop"),
    ]
    
    # 关键词映射
    keywords = {
        "微信": ["wechat", "weixin"], "wechat": ["wechat", "weixin"],
        "qq": ["qq", "tencent"], "chrome": ["chrome", "google"],
        "edge": ["msedge", "edge"], "firefox": ["firefox", "mozilla"],
        "vscode": ["code", "vscode"], "idea": ["idea", "intellij"],
        "pycharm": ["pycharm"], "钉钉": ["dingtalk"], "飞书": ["feishu", "lark"],
        "网易云": ["cloudmusic", "netease"], "spotify": ["spotify"],
        "steam": ["steam"], "discord": ["discord"], "telegram": ["telegram"],
        "word": ["winword", "word"], "excel": ["excel"],
        "ppt": ["powerpnt", "powerpoint"], "outlook": ["outlook"],
    }
    
    search_keywords = keywords.get(app_lower, [app_lower])
    
    for base_path in search_paths:
        if not os.path.exists(base_path):
            continue
        for keyword in search_keywords:
            pattern = os.path.join(base_path, "**", f"*{keyword}*.exe")
            for match in glob.glob(pattern, recursive=True):
                if "unins" not in match.lower() and "update" not in match.lower():
                    return match
            pattern = os.path.join(base_path, "**", f"*{keyword}*.lnk")
            for match in glob.glob(pattern, recursive=True):
                return match
    
    # 搜索开始菜单
    start_menu_paths = [
        os.path.expandvars(r"%ProgramData%\Microsoft\Windows\Start Menu\Programs"),
        os.path.expandvars(r"%AppData%\Microsoft\Windows\Start Menu\Programs"),
    ]
    for base_path in start_menu_paths:
        if not os.path.exists(base_path):
            continue
        for keyword in search_keywords:
            pattern = os.path.join(base_path, "**", f"*{keyword}*.lnk")
            for match in glob.glob(pattern, recursive=True):
                return match
    
    return None


def execute_delayed_action(task_id: str, action: str, params: dict):
    """执行延时动作"""
    try:
        if action == "open_app":
            app_name = params.get("app_name", "")
            executable = find_application(app_name)
            if executable:
                subprocess.Popen(f'start "" "{executable}"', shell=True,
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                print(f"[定时任务 {task_id}] 已打开: {app_name}")
            else:
                print(f"[定时任务 {task_id}] 找不到应用: {app_name}")
        elif action == "shutdown":
            os.system("shutdown /s /t 0")
        elif action == "restart":
            os.system("shutdown /r /t 0")
        elif action == "sleep":
            os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
        elif action == "lock":
            os.system("rundll32.exe user32.dll,LockWorkStation")
        elif action == "message":
            msg = params.get("message", "提醒时间到！")
            subprocess.Popen(f'msg * "{msg}"', shell=True,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print(f"[定时任务 {task_id}] 已显示消息: {msg}")
    except Exception as e:
        print(f"[定时任务 {task_id}] 执行失败: {e}")
    finally:
        scheduled_tasks.pop(task_id, None)


@router.get("/time")
async def get_system_time():
    """获取系统时间"""
    now = datetime.now()
    return {
        "timestamp": now.timestamp(),
        "datetime": now.strftime("%Y-%m-%d %H:%M:%S"),
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M:%S"),
        "timezone": str(now.astimezone().tzinfo),
        "weekday": ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][now.weekday()],
        "platform": platform.system()
    }


@router.post("/open-app")
async def open_application(request: OpenAppRequest):
    """智能打开应用程序"""
    executable = find_application(request.app_name)
    
    if not executable:
        return {
            "success": False,
            "message": f"找不到应用: {request.app_name}",
            "suggestion": "请确认应用已安装，或尝试使用应用的英文名"
        }
    
    try:
        subprocess.Popen(f'start "" "{executable}"', shell=True,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return {"success": True, "message": f"已启动: {request.app_name}", "path": executable}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"启动失败: {str(e)}")


@router.post("/delay")
async def create_delayed_task(request: DelayedTaskRequest):
    """创建延时任务"""
    task_id = str(uuid.uuid4())[:8]
    
    supported_actions = ["open_app", "shutdown", "restart", "sleep", "lock", "message"]
    if request.action not in supported_actions:
        return {
            "success": False,
            "message": f"不支持的动作: {request.action}",
            "supported_actions": supported_actions
        }
    
    timer = threading.Timer(
        request.delay_seconds,
        execute_delayed_action,
        args=[task_id, request.action, request.params]
    )
    timer.start()
    
    scheduled_tasks[task_id] = {
        "action": request.action,
        "params": request.params,
        "delay_seconds": request.delay_seconds,
        "created_at": datetime.now().strftime("%H:%M:%S"),
        "timer": timer
    }
    
    return {
        "success": True,
        "task_id": task_id,
        "message": f"已创建定时任务，将在 {request.delay_seconds} 秒后执行 {request.action}"
    }


@router.delete("/delay/{task_id}")
async def cancel_delayed_task(task_id: str):
    """取消延时任务"""
    if task_id not in scheduled_tasks:
        return {"success": False, "message": f"任务 {task_id} 不存在"}
    
    task = scheduled_tasks.pop(task_id)
    task["timer"].cancel()
    return {"success": True, "message": f"已取消任务 {task_id}"}


@router.get("/delay")
async def list_delayed_tasks():
    """列出所有延时任务"""
    tasks = [{
        "task_id": tid,
        "action": t["action"],
        "params": t["params"],
        "created_at": t["created_at"]
    } for tid, t in scheduled_tasks.items()]
    return {"tasks": tasks}
