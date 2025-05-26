import traceback
import uuid

from fastapi import APIRouter, HTTPException, BackgroundTasks, File, UploadFile, Path

from database.store import StoreEntity
from database.task import TaskEntity, FileTaskEntity
from service.create_store import CreateData, create, check_task_status, FileCreate, add_store_file
from service.delete_store import FileDelete, store_file_delete, store_delete
from service.list_store import store_file_list, store_list
from service.min_io import upload, download
from service.retrieve_store import RetrieveData, retrieve
from utils.log import log

router = APIRouter(prefix='/v1')


@router.post("/upload", description="文件上传接口")
async def upload_file(file: UploadFile = File(...)):
    try:
        log.info(f"文件{file.filename}上传")
        file_id = await upload(file)
        return {"code": 0, "msg": f"文件 '{file.filename}' 上传成功！", "file_id": file_id}
    except Exception as e:
        trace_info = traceback.format_exc()
        log.error(f'/v1/vector_store/upload/ 异常, 文件名: {file.filename}, 错误: {e}, 堆栈: {trace_info}')
        raise HTTPException(status_code=500, detail=f"文件{file.filename}上传失败:{e}")


@router.get("/download/{file_name}", description="文件下载接口")
async def download_file(file_name: str = Path(description="文件名称")):
    try:
        log.info(f"文件下载:{file_name}")
        response = download(file_name)
        return response
    except Exception as e:
        trace_info = traceback.format_exc()
        log.error(f'/v1/vector_store/download_file/ 异常, 文件名: {file_name}, 错误: {e}, 堆栈: {trace_info}')
        raise HTTPException(status_code=500, detail=f"MinIO 错误: {e}")


@router.post("/vector_store/create", description="知识库创建接口")
async def vector_store_create(data: CreateData, background_tasks: BackgroundTasks):
    try:
        task_id = str(uuid.uuid4())
        index_id = task_id
        log.info(f"接收知识库创建请求:{data}， 任务：{task_id}")
        TaskEntity.create(task_id=task_id, index_id=index_id, index_name=data.index_name, status="Running")
        for file_data in data.files:
            FileTaskEntity.create(task_id=task_id, file_id=file_data.file_id, file_name=file_data.file_name,
                                  status="Running")
        background_tasks.add_task(create, data, task_id)
        # create(data, task_id)
        log.info(f"知识库创建后台任务启动， 任务：{task_id}")
        return {"code": 0, "msg": "ok", "task_id": f'{task_id}'}
    except Exception as e:
        trace_info = traceback.format_exc()
        log.error(f'/v1/vector_store/create/ 异常, 请求: {data}, 错误: {e}, 堆栈: {trace_info}')
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/vector_store/get_task_status/{task_id}", description="知识库创建任务查询接口")
async def get_task_status(task_id: str):
    log.info(f"知识库创建任务查询,task_id:{task_id}")
    result = check_task_status(task_id)
    if result is not None:
        log.info(f"知识库创建任务查询成功,任务:{task_id},状态为:{result}")
        result.update({"code": 0, "msg": "ok"})
        return result
    return {"code": -1, "msg": "task or task_status not exists"}


@router.post("/vector_store/retrieve", description="知识库检索接口")
async def vector_store_retrieve(data: RetrieveData):
    log.info(f'知识库检索{data}')
    try:
        result = await retrieve(data)
        log.info(f"检索结果返回成功:{result}")
        return {"code": 0, "msg": "ok", "chunks": result["retriever_doc"]}
    except Exception as e:
        trace_info = traceback.format_exc()
        log.error(f'/v1/vector_store/retrieve/ 异常, 请求: {data}, 错误: {e}, 堆栈: {trace_info}')
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/vector_store/file/create", description="知识库文件上传")
async def vector_store_file_create(data: FileCreate, background_tasks: BackgroundTasks):
    try:
        index_id = data.index_id
        log.info(f"接收到知识库文件上传请求:{data},知识库 ID:{index_id}")
        # 判断知识库 ID 对应的知识库是否存在
        store_entity = StoreEntity.query_first(index_id=index_id)
        if store_entity is None:
            log.error(f"Index Id 为:{index_id}的知识库不存在")
            return {"code": 400, "msg": "Index Id 为:{index_id}的知识库不存在"}
        index_name = store_entity.index_name
        task_id = str(uuid.uuid4())

        TaskEntity.create(task_id=task_id, index_id=index_id, index_name=index_name, status="Running")
        for file_data in data.files:
            FileTaskEntity.create(task_id=task_id, file_id=file_data.file_id, file_name=file_data.file_name,
                                  status="Running")
        background_tasks.add_task(add_store_file, data, task_id)
        log.info(f"知识库文件添加任务启动， 任务：{task_id}")
        return {"code": 0, "msg": "ok", "task_id": f'{task_id}'}
    except Exception as e:
        trace_info = traceback.format_exc()
        log.error(f'/v1/vector_store/file/create/ 异常, 请求: {data}, 错误: {e}, 堆栈: {trace_info}')
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/vector_store/file/delete", description="知识库文件删除")
async def vector_store_file_delete(data: FileDelete):
    try:
        index_id = data.index_id
        store = StoreEntity.query_first(index_id=index_id)
        if store is None:
            log.error(f"store:{index_id} not exists")
            return {"code": -1, "msg": f"知识库{index_id}不存在"}
        store_file_delete(data)
        return {"code": 0, "msg": "ok"}
    except Exception as e:
        trace_info = traceback.format_exc()
        log.error(f"/vector_store/file/delete 异常,请求: {data}, 错误: {e}, 堆栈: {trace_info}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/vector_store/file/list/{index_id}", description="知识库文件列表")
async def vector_store_file_list(index_id: str = Path(description="知识库ID")):
    store_entity = StoreEntity.query_first(index_id=index_id)
    if store_entity is None:
        log.info(f"store:{index_id} not exists")
        return {"code": -1, "msg": f"ID为{index_id}的知识库不存在"}

    file_list = store_file_list(index_id)
    return {"code": 0, "msg": "ok", "file_list": {file_list}}


@router.get("/vector_store/list", description="知识库列表")
async def vector_store_list():
    _store_list = store_list()
    return {"code": 0, "msg": "ok", "store_list": _store_list}


@router.post("/vector_store/delete/{index_id}", description="删除知识库")
async def vector_store_delete(index_id: str):
    store_entity = StoreEntity.query_first(index_id=index_id)
    if store_entity is None:
        log.error(f"store:{index_id} not exists")
        return {"code": 400, "msg": f"删除失败,知识库:{index_id}不存在"}

    store_delete(index_id)
    return {"code": 0, "msg": "ok"}
