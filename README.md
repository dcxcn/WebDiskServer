# WebDiskServer
使用fastApi + jinja2 开发的 网盘服务, 通过指定 操作系统上硬盘上的某个路径，能在网页上展示文件、上传文件、搜索文件、下载文件，可以配置单用户 用户名密码

nuitka --standalone --mingw64 --show-memory --show-progress --nofollow-imports --plugin-enable=qt-plugins --follow-import-to=need  --output-dir=o app.py