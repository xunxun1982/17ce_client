# 安装步骤
## Linux (Ubuntu\Debian)
如未安装过Python 2.7, 执行以下命令安装
```
sudo apt-get update
sudo apt-get install python2.7 python2.7-dev python-pip
```
安装完毕后, 安装客户端所需依赖模块
```
pip install twisted autobahn pycurl pyping
```
## Windows
如未安装过Python 2.7，上Python官网下载2.7版本安装，完成后安装VC编译器
[点这里下载](https://www.microsoft.com/en-us/download/details.aspx?id=44266)

全部完成后假定你安装到 C:\Python27，那么在命令提示符(注意管理员权限)中执行
```
C:\Python27\Scripts\pip.exe install twisted autobahn pycurl pyping
```

# 设置方法
将脚本放置到一个路径中(最好不要有空格和中文), 修改以下部分, 注意不要修改缩进距离
```
self.USERNAME = "xxx@xxx.com"  # modify to your username(email)
self.UUID = hex(uuid.getnode())[2:-1]  # modify to your uuid or keep default
self.LOCALIP = "192.168.1.1"  # modify to your local ip (optional)
self.DNSIP = "127.0.0.1"  # modify to your dns ip (optional)
```
将xxx@xxx.com替换为你的用户名

如果你已知自己的UUID (比如是1234567890abcdef) 想替换进去，将hex(uuid.getnode())[2:-1]替换成"1234567890abcdef", 如果不知道或者想开新的监控点，那就保持默认, 会自动生成UUID



举例:

我的帐号: 12345@qq.com

UUID: 1234567890abcdef

那么修改成如下:
```
self.USERNAME = "12345@qq.com"  # modify to your username(email)
self.UUID = "1234567890abcdef"  # modify to your uuid or keep default
self.LOCALIP = "192.168.1.1"  # modify to your local ip (optional)
self.DNSIP = "127.0.0.1"  # modify to your dns ip (optional)
```

# 启动方法
注意需要使用root或管理员权限
## Linux
```
python 17ce_client.py
```
## Windows
命令提示符(管理员权限)下执行
```
C:\Python27\python.exe 17ce_client.py
```
如果脚本放别的地方，比如D盘
```
C:\Python27\python.exe D:\17ce_client.py
```

# DIY
至于如何自己修改获取任务频率、如何获得更多任务……自己琢磨吧
