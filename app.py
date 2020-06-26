from fastapi import FastAPI, Form, File, UploadFile
from pydantic import BaseModel
import uvicorn as u
from starlette.requests import Request
from starlette.responses import RedirectResponse, FileResponse
from starlette.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
import os
import time
import configparser

config = configparser.ConfigParser()

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key='YOUR KEY')
app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")


def split_path(path):
    path_list = path.split('/')
    path_list = [[path_list[i - 1], '/'.join(path_list[:i])] for i in range(1, len(path_list) + 1)]
    return path_list


templates.env.filters["split_path"] = split_path

# 判断配置文件是否存在,不存在就创建
if os.path.exists(os.getcwd() + "/config.ini"):
    config.read("./config.ini")
else:
    config["DEF"] = {
        'port': 8080,
        'basedir': os.getcwd(),
        'secret_key': "dcx",
        'uname': "dcx",
        'upwd': "123"
    }
    with open('config.ini', 'w') as f:
        config.write(f)
context_path = config.get('DEF', 'context_path')


class User(BaseModel):
    username: str = None
    password: str = None


@app.get('/')
@app.get(context_path)
def index_get(request: Request):
    return RedirectResponse(context_path + '/login')


@app.get(context_path + '/login')
def login_get(request: Request):
    if request.session.get('username'):
        return RedirectResponse(context_path + '/index')
    return templates.TemplateResponse('account.html', {"request": request})


@app.post(context_path + '/doLogin')
def login_post(request: Request, user: User):
    print('username', user.username)
    print('password', user.password)
    if user.username == 'dcx' and user.password == '123':
        request.session['username'] = user.username
        return {"code": 200, "error": ""}
    else:
        return {"code": 401, "error": "用户名或密码错误"}


@app.route(context_path + '/logout')
def logout(request: Request):
    del request.session['username']
    return RedirectResponse(context_path + '/login')


@app.get(context_path + '/index')
@app.get(context_path + '/index/{path_uri:path}')
def index(request: Request, path_uri=''):
    if not request.session.get('username'):
        return RedirectResponse(context_path + '/login')
    base_dir = config.get('DEF', 'basedir')
    path_url2 = path_uri.replace('index', '/')
    real_path = os.path.join(base_dir, path_url2).replace('\\', '/')
    if not os.path.exists(real_path):
        return templates.TemplateResponse('index.html', {"request": request, "error_info": "错误的路径..."})
    file_reader = DocumentReader(real_path)
    dirs, files = file_reader.analysis_dir()
    data = {"request": request, "context_path": context_path, "path": path_url2, "dirs": dirs, "files": files, "sfiles": [], "error_info": None}

    return templates.TemplateResponse('index.html', data)


@app.get(context_path + '/search')
def index(request: Request, searchText: str):
    base_dir = config.get('DEF', 'basedir')
    file_reader = DocumentReader(base_dir)
    sfiles = file_reader.search_file(searchText, base_dir)
    data = {"request": request, "context_path": context_path,  "path": "", "dirs": [], "files": [], "sfiles": sfiles, "error_info": None}
    return templates.TemplateResponse('index.html', data)


@app.post(context_path + '/upload')
async def upload(upload_path: str = Form(...), upload_file: UploadFile = Form(...)):
    path = upload_path
    file_name = upload_file.filename
    base_dir = config.get('DEF', 'basedir')
    contents = await upload_file.read()
    with open(os.path.join(base_dir, path, file_name), 'wb') as f:
        f.write(contents)
    return {"code": 200, "info": "文件：%s 上传成功" % file_name}


@app.get(context_path + '/download/{filename}')
@app.get(context_path + '/download/{path:path}/{filename}')
async def download(filename, path=None):
    if not path:
        real_path = config.get('DEF', 'basedir')
    else:
        real_path = os.path.join(config.get('DEF', 'basedir'), path)
    return FileResponse(real_path + '/' + filename)


class DocumentReader:
    def __init__(self, real_path):
        self.real_path = real_path

    def analysis_dir(self):
        dirs = []
        files = []
        curdir = os.getcwd()
        print('curDir1=' + curdir)
        os.chdir(self.real_path)
        for name in sorted(os.listdir('.'), key=lambda x: x.lower()):
            _time = time.strftime("%Y/%m/%d %H:%M", time.localtime(os.path.getctime(name)))
            if os.path.isdir(name):
                dirs.append([name, _time, '文件夹', '-'])
            elif os.path.isfile(name):
                file_type = os.path.splitext(name)[1]
                size = self.get_size(os.path.getsize(name))
                files.append([name, _time, file_type, size])
        os.chdir(curdir)
        curdir = os.getcwd()
        print('curDir2=' + curdir)
        return dirs, files

    @staticmethod
    def get_size(size):
        if size < 1024:
            return '%d  B' % size
        elif 1024 <= size < 1024 * 1024:
            return '%.2f KB' % (size / 1024)
        elif 1024 * 1024 <= size < 1024 * 1024 * 1024:
            return '%.2f MB' % (size / (1024 * 1024))
        else:
            return '%.2f GB' % (size / (1024 * 1024 * 1024))

    def search_file(self, filename, path):
        '''search a file in target directory
        :param filename: file to be searched
        :param path: search scope
        :return:file list
        '''
        curdir = os.getcwd()
        print('curDir1=' + curdir)
        flag = False
        count = 0
        result_list = []
        if os.path.exists(path):
            for root, dirs, files in os.walk(path):
                for fname in files:
                    os.chdir(root)
                    cu_path = root + "\\" + fname
                    if fname.lower().find(filename.lower()) != -1 and os.path.isfile(cu_path):
                        print(":::Find it,file no", count + 1, ":", cu_path)
                        _time = time.strftime("%Y/%m/%d %H:%M", time.localtime(os.path.getctime(fname)))
                        file_type = os.path.splitext(fname)[1]
                        size = self.get_size(os.path.getsize(fname))
                        cur_dir = (root + "\\").replace(path + "\\", '')
                        # 为了前端路径斜杠显示一致
                        cur_dir = cur_dir.replace("\\", '/')
                        flag = True
                        count += 1
                        result_list.append([fname, _time, file_type, size, cur_dir])
            if flag is False:
                print(":::Not found the file:", filename, "in path:", path)
                os.chdir(curdir)
                curdir = os.getcwd()
                print('curDir2=' + curdir)
                return result_list

            else:
                print("======== Get[", count, "]files ========")
                os.chdir(curdir)
                curdir = os.getcwd()
                print('curDir2=' + curdir)
                return result_list
        else:
            print("!!-----path not existed:", path)
            os.chdir(curdir)
            curdir = os.getcwd()
            print('curDir2=' + curdir)
            return result_list


if __name__ == '__main__':
    u.run(app, host=config.get('DEF', 'host'), port=int(config.get('DEF', 'port')))
