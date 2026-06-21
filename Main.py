from loguru import logger
from config.loggerConfig import LoggerConfigurator
from service.WebEdgeService import WebEdgeService
from config.JsonLoadConfig import resolve_driver_exe_path
from config.webdriverConfig import WebDriverConfigurator
from config.platformConfig import PLATFORM_NAMES


PLATFORM_OPTIONS = {
    "1": "zhihuishu",
    "2": "chaoxing",
}


def select_platform() -> str:
    """选择目标平台"""
    print("\n" + "=" * 40)
    print("  请选择目标学习平台：")
    print("=" * 40)
    for key, name in PLATFORM_NAMES.items():
        print(f"  [{key}] {name}")
    print("=" * 40)

    while True:
        choice = input("请输入选项 (1/2): ").strip()
        if choice in PLATFORM_OPTIONS:
            return PLATFORM_OPTIONS[choice]
        print("无效选项，请输入 1 或 2")


def main():
    LoggerConfigurator().setup()

    # 选择平台
    platform = select_platform()
    driver_exe = resolve_driver_exe_path()
    configurator = WebDriverConfigurator(driver_path=driver_exe, platform=platform)
    web_service = WebEdgeService(configurator=configurator, platform=platform)

    try:
        while True:
            print("\n" + "=" * 60)
            exam_url = input(f"请粘贴{PLATFORM_NAMES[platform]}答题网址 (输入 q 退出): ").strip()
            if not exam_url:
                logger.warning("未输入答题网址，请重新输入。")
                continue
            if exam_url.lower() == "q":
                logger.info("用户选择退出，清理浏览器...")
                try:
                    web_service._save_cookies()
                    if web_service.driver:
                        web_service.driver.quit()
                except Exception:
                    pass
                break
            logger.info(f"答题网址: {exam_url}")
            web_service.run_exam(exam_url)
    except KeyboardInterrupt:
        logger.info("用户强制退出。")


if __name__ == "__main__":
    main()

"⣇⣿⠘⣿⣿⣿⡿⡿⣟⣟⢟⢟⢝⠵⡝⣿⡿⢂⣼⣿⣷⣌⠩⡫⡻⣝⠹⢿⣿⣷"
"⡆⣿⣆⠱⣝⡵⣝⢅⠙⣿⢕⢕⢕⢕⢝⣥⢒⠅⣿⣿⣿⡿⣳⣌⠪⡪⣡⢑⢝⣇"
"⡆⣿⣿⣦⠹⣳⣳⣕⢅⠈⢗⢕⢕⢕⢕⢕⢈⢆⠟⠋⠉⠁⠉⠉⠁⠈⠼⢐⢕⢽"
"⡗⢰⣶⣶⣦⣝⢝⢕⢕⠅⡆⢕⢕⢕⢕⢕⣴⠏⣠⡶⠛⡉⡉⡛⢶⣦⡀⠐⣕⢕"
"⡝⡄⢻⢟⣿⣿⣷⣕⣕⣅⣿⣔⣕⣵⣵⣿⣿⢠⣿⢠⣮⡈⣌⠨⠅⠹⣷⡀⢱⢕"
"⡝⡵⠟⠈⢀⣀⣀⡀⠉⢿⣿⣿⣿⣿⣿⣿⣿⣼⣿⢈⡋⠴⢿⡟⣡⡇⣿⡇⡀⢕"
"⡝⠁⣠⣾⠟⡉⡉⡉⠻⣦⣻⣿⣿⣿⣿⣿⣿⣿⣿⣧⠸⣿⣦⣥⣿⡇⡿⣰⢗⢄"
"⠁⢰⣿⡏⣴⣌⠈⣌⠡⠈⢻⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣬⣉⣉⣁⣄⢖⢕⢕⢕"
"⡀⢻⣿⡇⢙⠁⠴⢿⡟⣡⡆⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣷⣵⣵⣿"
"⡻⣄⣻⣿⣌⠘⢿⣷⣥⣿⠇⣿⣿⣿⣿⣿⣿⠛⠻⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿"
"⣷⢄⠻⣿⣟⠿⠦⠍⠉⣡⣾⣿⣿⣿⣿⣿⣿⢸⣿⣦⠙⣿⣿⣿⣿⣿⣿⣿⣿⠟"
"⡕⡑⣑⣈⣻⢗⢟⢞⢝⣻⣿⣿⣿⣿⣿⣿⣿⠸⣿⠿⠃⣿⣿⣿⣿⣿⣿⡿⠁⣠"
"⡝⡵⡈⢟⢕⢕⢕⢕⣵⣿⣿⣿⣿⣿⣿⣿⣿⣿⣶⣶⣿⣿⣿⣿⣿⠿⠋⣀⣈⠙"
"⡝⡵⡕⡀⠑⠳⠿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠿⠛⢉⡠⡲⡫⡪⡪⡣"