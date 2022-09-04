# 前端
1. 下载安装nodejs
    ```shell
    cd /usr/local
    wget https://nodejs.org/dist/v16.17.0/node-v16.17.0-linux-x64.tar.xz
    tar -xvf node-v16.17.0-linux-x64.tar.xz
    mv node-v16.17.0-linux-x64 node
    ```
2. 将 /usr/local/node/bin 添加到环境变量
3. 测试安装成功
    ```shell
    node -v
    npm -v
    ```
4. 安装第三方模块
   ```shell
   cd sam/dashboard/frontend
   npm install
   ```
5. 修改后端地址
   ```shell
   cd sam/dashboard/frontend
   vim .env.development
   ```
   修改其中`VUE_APP_API_BASE_URL`为后端部署地址

# 后端
1. 安装django
   ```shell
   pip3 install django django-cors-headers
   ```

# 运行
1. 启动dispacher, mediator, simulator, measurer, regulator
2. 运行后端
   ```shell
   cd sam/simulator/dashboard/backend
   python3 manager.py runserver 0.0.0.0:8000
   ```
3. 运行前端
   ```shell
   cd sam/simulator/dashboard/frontend
   npm run serve
   ```
4. 访问前端部署主机的8080端口