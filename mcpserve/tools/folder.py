"""文件夹工具 - 文件夹搜索、打开"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import subprocess
import os
import glob

router = APIRouter(prefix="/folder", tags=["文件夹"])


class SearchFolderRequest(BaseModel):
    folder_name: str
    search_path: str = ""
    max_results: int = 10


class OpenFolderRequest(BaseModel):
    folder_path: str


class CreateFolderRequest(BaseModel):
    folder_path: str


def get_default_search_paths() -> list:
    """获取默认搜索路径"""
    user_profile = os.path.expandvars(r"%UserProfile%")
    return [
        os.path.join(user_profile, "Desktop"),
        os.path.join(user_profile, "Documents"),
        os.path.join(user_profile, "Downloads"),
        user_profile,
        "C:\\",
        "D:\\",
        "E:\\",
    ]


@router.post("/search")
async def search_folder(request: SearchFolderRequest):
    """搜索文件夹"""
    folder_name = request.folder_name
    max_results = request.max_results
    
    search_paths = [request.search_path] if request.search_path else get_default_search_paths()
    
    results = []
    
    for base_path in search_paths:
        if not os.path.exists(base_path):
            continue
        
        try:
            pattern = os.path.join(base_path, "**", f"*{folder_name}*")
            for match in glob.glob(pattern, recursive=True):
                if os.path.isdir(match):
                    results.append({
                        "path": match,
                        "name": os.path.basename(match)
                    })
                    if len(results) >= max_results:
                        break
        except Exception as e:
            print(f"搜索 {base_path} 出错: {e}")
        
        if len(results) >= max_results:
            break
    
    return {
        "success": True,
        "count": len(results),
        "folders": results
    }


@router.post("/open")
async def open_folder(request: OpenFolderRequest):
    """在资源管理器中打开文件夹"""
    folder_path = request.folder_path
    
    if not os.path.exists(folder_path):
        return {"success": False, "message": f"文件夹不存在: {folder_path}"}
    
    if not os.path.isdir(folder_path):
        return {"success": False, "message": f"不是文件夹: {folder_path}"}
    
    try:
        subprocess.Popen(f'explorer "{folder_path}"', shell=True,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return {
            "success": True,
            "message": f"已打开文件夹: {os.path.basename(folder_path)}",
            "path": folder_path
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"打开失败: {str(e)}")


@router.post("/create")
async def create_folder(request: CreateFolderRequest):
    """创建文件夹"""
    folder_path = request.folder_path
    
    if os.path.exists(folder_path):
        return {"success": False, "message": f"文件夹已存在: {folder_path}"}
    
    try:
        os.makedirs(folder_path)
        return {
            "success": True,
            "message": f"已创建文件夹: {os.path.basename(folder_path)}",
            "path": folder_path
        }
    except Exception as e:
        return {"success": False, "message": f"创建文件夹失败: {str(e)}"}
