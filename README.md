## 原因
由于为了补那个线上课，选的这个sb网课太他妈多了，我是真的没招了，我要是一个一个刷的话我都不知道刷到什么时候，还有什么章节测试，我头都大了，但是还是得认命，后面天天逛github康康有没有什么好东西，但是吧，刷课的有位大佬写的确实好用，但是不能做那个章节测试，这就很可惜。
后面我去找了很多都很不行，没办法。我只能自己写了，将就着一个模板往上套屎山，那个屎山代码真的越堆越多，我自己看着的寒碜，不过好歹能用了，将就了吧。网课日期快到了并且这个sb学校天天鸟事太多了，琢磨代码的时间都没有，只能用一下claude来提一下速，花了我500多万token，难受。本来想要改一下我的屎山的，结果发现越改越多
后面我都随缘了，看着没太多bug将就有用就行了。现象目前是稍微好用点的版本，虽然还有不少bug不过差不多了，后面我有时间的话尽量改一下bug，反正目前能够正常刷那个智慧树的章节测试了将就吧
## 这是个啥
这就是个自动刷智慧树里面的章节测试和考试，这样可以不用一个一个的复制给豆包啦，哈哈哈哈哈哈哈哈哈
## 怎么用
1. 至少安装Python 3.10+
2. 安装依赖
```bash
pip install -r requirements.txt
```
3. 配一下Edge WebDriver吧（因为我这个是通过截屏网页来识别题目的，但是我在开源的源码里面是带的有的，如果不能用的话就自己去下）
  - 下载WebDriver的地址：[Edge WebDriver](https://msedgedriver.microsoft.com/141.0.3537.99/edgedriver_win64.zip)
  - 下载完成后，将`edgedriver_win64.zip`文件解压到`tools`根目录下
  - 解压好后的文件结构应是
```
tools/
├── edgedriver_win64
├── llms
```
4. 配置文件（因为我这个是调用那个deepseek的api_key来获取答案的，本来想直接伪造deepseek的网页请求包的，但是太不稳定了，只能出此下策）
   - 在项目根目录下打开`config.json`文件，配置好DeepSeek API Key
   - 在根目录下的config.json里面的“deep_seek的api_key换成你自己的就行”
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
5.配置好了后，就直接在目录下的cmd终端输入python main.py就行

## 怎么获得deepseek的API_Key
 注意：需要充值才能使用API，金额无所谓啦（因为就算你刷了两三个网课的所有章节测试，一般一块钱都花不到），充值后即可使用
1. 访问[DeepSeek API](https://platform.deepseek.com/)
2. 在`密码登录`中点击`立即注册`按钮
3. 填写注册信息
4. 注册成功后，登录账号
5. 在左侧侧边栏点击`API keys`
6. 点击`创建 API Key`按钮
7. 填写API Key名称
8. 点击`创建`按钮
9. 创建好后点击`复制`，然后粘贴在config'.json里面去
## 注意一下 ##
因为这个屎山有点多，可能会出现小bug，我实在没时间修复了，那个答完题的网页，先回到智慧树的首页，再复制你要答题的链接，不然会出bug，有时候跳题，跳题的话直接随便选吧，后面我抽时间会修一下的，能用的话先将就用吧，多多少少还是能够轻松点
