"""文件工具 - 文件和文件夹搜索、打开"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime
import subprocess
import os
import glob

router = APIRouter(prefix="/file", tags=["文件"])


class SearchFileRequest(BaseModel):
    filename: str
    search_path: str = ""
    max_results: int = 10


class OpenFileRequest(BaseModel):
    file_path: str


class CreateFileRequest(BaseModel):
    file_path: str
    content: str = ""


class ReadFileRequest(BaseModel):
    file_path: str
    max_size: int = 102400  # 默认最大读取100KB


class WriteFileRequest(BaseModel):
    file_path: str
    content: str
    mode: str = "overwrite"  # overwrite 或 append


def get_default_search_paths() -> list:
    """获取默认搜索路径"""
    user_profile = os.path.expandvars(r"%UserProfile%")
    return [
        os.path.join(user_profile, "Desktop"),
        os.path.join(user_profile, "Documents"),
        os.path.join(user_profile, "Downloads"),
        os.path.join(user_profile, "Pictures"),
        os.path.join(user_profile, "Videos"),
        os.path.join(user_profile, "Music"),
        user_profile,
        "D:\\",
        "E:\\",
    ]


@router.post("/search")
async def search_file(request: SearchFileRequest):
    """搜索文件"""
    filename = request.filename
    max_results = request.max_results
    
    search_paths = [request.search_path] if request.search_path else get_default_search_paths()
    
    results = []
    searched_paths = []
    
    for base_path in search_paths:
        if not os.path.exists(base_path):
            continue
        
        searched_paths.append(base_path)
        
        try:
            pattern = os.path.join(base_path, "**", f"*{filename}*")
            for match in glob.glob(pattern, recursive=True):
                if os.path.isfile(match):
                    try:
                        stat = os.stat(match)
                        results.append({
                            "path": match,
                            "name": os.path.basename(match),
                            "size": stat.st_size,
                            "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                        })
                    except:
                        pass
                    if len(results) >= max_results:
                        break
        except Exception as e:
            print(f"搜索 {base_path} 出错: {e}")
        
        if len(results) >= max_results:
            break
    
    return {
        "success": True,
        "count": len(results),
        "files": results,
        "searched_paths": searched_paths
    }


@router.post("/open")
async def open_file(request: OpenFileRequest):
    """用默认程序打开文件"""
    file_path = request.file_path
    
    if not os.path.exists(file_path):
        return {"success": False, "message": f"文件不存在: {file_path}"}
    
    try:
        subprocess.Popen(f'start "" "{file_path}"', shell=True,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return {
            "success": True,
            "message": f"已打开: {os.path.basename(file_path)}",
            "path": file_path
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"打开失败: {str(e)}")


@router.post("/create")
async def create_file(request: CreateFileRequest):
    """创建文件"""
    file_path = request.file_path
    
    # 确保父目录存在
    parent_dir = os.path.dirname(file_path)
    if parent_dir and not os.path.exists(parent_dir):
        try:
            os.makedirs(parent_dir)
        except Exception as e:
            return {"success": False, "message": f"创建目录失败: {str(e)}"}
    
    # 检查文件是否已存在
    if os.path.exists(file_path):
        return {"success": False, "message": f"文件已存在: {file_path}"}
    
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(request.content)
        return {
            "success": True,
            "message": f"已创建文件: {os.path.basename(file_path)}",
            "path": file_path
        }
    except Exception as e:
        return {"success": False, "message": f"创建文件失败: {str(e)}"}


@router.post("/read")
async def read_file(request: ReadFileRequest):
    """读取文件内容"""
    file_path = request.file_path
    
    if not os.path.exists(file_path):
        return {"success": False, "message": f"文件不存在: {file_path}"}
    
    if not os.path.isfile(file_path):
        return {"success": False, "message": f"不是文件: {file_path}"}
    
    try:
        file_size = os.path.getsize(file_path)
        
        if file_size > request.max_size:
            return {
                "success": False,
                "message": f"文件过大 ({file_size} bytes)，超过限制 ({request.max_size} bytes)"
            }
        
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        return {
            "success": True,
            "path": file_path,
            "name": os.path.basename(file_path),
            "size": file_size,
            "content": content
        }
    except UnicodeDecodeError:
        return {"success": False, "message": "文件不是文本文件，无法读取"}
    except Exception as e:
        return {"success": False, "message": f"读取文件失败: {str(e)}"}



@router.post("/write")
async def write_file(request: WriteFileRequest):
    """写入文件内容"""
    file_path = request.file_path
    
    # 确保父目录存在
    parent_dir = os.path.dirname(file_path)
    if parent_dir and not os.path.exists(parent_dir):
        try:
            os.makedirs(parent_dir)
        except Exception as e:
            return {"success": False, "message": f"创建目录失败: {str(e)}"}
    
    try:
        # 根据模式选择写入方式
        if request.mode == "append":
            write_mode = "a"
        else:
            write_mode = "w"
        
        with open(file_path, write_mode, encoding="utf-8") as f:
            f.write(request.content)
        
        file_size = os.path.getsize(file_path)
        
        return {
            "success": True,
            "message": f"已{'追加' if request.mode == 'append' else '写入'}文件: {os.path.basename(file_path)}",
            "path": file_path,
            "size": file_size
        }
    except Exception as e:
        return {"success": False, "message": f"写入文件失败: {str(e)}"}


@router.delete("/delete")
async def delete_file(file_path: str):
    """删除文件"""
    if not os.path.exists(file_path):
        return {"success": False, "message": f"文件不存在: {file_path}"}
    
    if not os.path.isfile(file_path):
        return {"success": False, "message": f"不是文件: {file_path}"}
    
    try:
        os.remove(file_path)
        return {
            "success": True,
            "message": f"已删除文件: {os.path.basename(file_path)}",
            "path": file_path
        }
    except Exception as e:
        return {"success": False, "message": f"删除文件失败: {str(e)}"}
