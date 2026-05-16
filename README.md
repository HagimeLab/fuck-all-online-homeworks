## 这是个啥
由于为了补那个线上课，选的这个sb网课太他妈多了，我是真的没招了，我要是一个一个刷的话我都不知道刷到什么时候，还有什么章节测试，我头都大了，但是还是得认命，后面天天逛github康康有没有什么好东西，但是吧，刷课的有位大佬写的确实好用，但是不能做那个章节测试，这就很可惜。
后面我去找了很多都很不行，没办法。我只能自己写了，将就着一个模板往上套屎山，那个屎山代码真的越堆越多，我自己看着的寒碜，不过好歹能用了，将就了吧。网课日期快到了并且这个sb学校天天鸟事太多了，琢磨代码的时间都没有，只能用一下claude来提一下速，并且改一下我的屎山，结果发现越改越多
后面我都随缘了，看着没太多bug将就有用就行了。现象目前是稍微好用点的版本，虽然还有不少bug不过差不多了，后面我有时间的话尽量改一下bug，反正目前能够正常刷那个智慧树的章节测试了将就吧
## 怎么用
1. 至少安装Python 3.10+
2. 安装依赖
```bash
pip install -r requirements.txt
```
3. 配一下Edge WebDriver吧（因为我这个是通过截屏网页来识别题目的，但是我在开源的源码里面是带的有的，如果不能用的话就自己去下）
 1、首先下载WebDriver，下载地址：[Edge WebDriver](https://msedgedriver.microsoft.com/141.0.3537.99/edgedriver_win64.zip)
 2、下载完成后，将`edgedriver_win64.zip`文件解压到`tools`根目录下
 3、解压好后的文件结构应是
```
tools/
├── edgedriver_win64
├── llms
```
4. 配置文件
   - 请在项目根目录下打开`config.json`文件，配置好DeepSeek API Key
   - 将你的DeepSeek API Key替换`YOUR_API_KEY`
   - 配置好的`config.json`例子如下
```json
{
  "llm": {
    "deepseek": {
      "api_key": "sk-xxxx",
      "base_url": "https://api.deepseek.com",
      "model": "deepseek-chat"
    }
  },
  "web_config": {
    "driver_path": "edgedriver_win64",
    "cookie_path": "edgedriver_win64/cookies.json"
  }
}
```
5. 运行脚本
   - 双击`run.bat`文件即可运行脚本


## 如何获取DeepSeek API Key
**注意：需要充值才能使用API，金额无所谓，充值后即可使用**
1. 访问[DeepSeek API](https://platform.deepseek.com/)
2. 在`密码登录`中点击`立即注册`按钮
3. 填写注册信息
4. 注册成功后，登录账号
5. 在左侧侧边栏点击`API keys`
6. 点击`创建 API Key`按钮
7. 填写API Key名称
8. 点击`创建`按钮
9. 创建好后点击`复制`，即可获取到你的API Key
10. 请将获取到的API Key替换`config.json`中的`YOUR_API_KEY`
