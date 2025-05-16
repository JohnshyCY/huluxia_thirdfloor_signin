import hashlib
import json
import os
import random
import time
import requests
from logger import logger
from notifier import get_notifier
from datetime import timezone
from datetime import datetime, timedelta  # 修改：添加timedelta

# 随机配置
phone_brand_type_list = list(["MI", "Huawei", "UN", "OPPO", "VO"])  # 随机设备厂商
device_code_random = random.randint(111, 987)  # 随机设备识别码

# 静态配置
platform = '2'
gkey = '000000'
app_version = '4.3.1.5.2'
versioncode = '398'
market_id = 'floor_web'
device_code = '%5Bd%5D5125c3c6-f' + str(device_code_random) + '-4c6b-81cf-9bc467522d61'
phone_brand_type = random.choice(phone_brand_type_list)
_key = ''
cat_id = ''  # 版块id
userid = ''  # 用户id
signin_continue_days = ''  # 连续签到天数
headers = {
    "Connection": "close",
    "Accept-Encoding": "gzip, deflate",
    "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
    "User-Agent": "okhttp/3.8.1",
    "Host": 'floor.huluxia.com'
}
session = requests.Session()
# 版块id
with open('cat_id.json', 'r', encoding='UTF-8') as f:
    content = f.read()
    cat_id_dict = json.loads(content)

class HuluxiaSignin:
    """
    葫芦侠三楼签到类
    """
    def __init__(self):
        """
        初始化类
        """
        self._key = ''
        self.cat_id = ''
        self.userid = ''
        self.signin_continue_days = ''

        # 初始化通知器类型
        notifier_type = os.getenv("NOTIFIER_TYPE", "none")
        config = {
            "webhook_url": os.getenv("WECHAT_ROBOT_URL"),
            "smtp_server": "smtp.qq.com",
            "port": 465
        }
        if notifier_type == "email":
            # 从环境变量获取邮箱配置
            email_config_str = os.getenv("EMAIL_CONFIG")
            if email_config_str:
                try:
                    email_config = json.loads(email_config_str)
                    config.update({
                        "username": email_config.get("username"),
                        "auth_code_or_password": email_config.get("auth_code_or_password"),
                        "sender_email": email_config.get("sender_email"),
                        "recipient_email": email_config.get("recipient_email")
                    })
                except json.JSONDecodeError:
                    print("邮箱配置格式错误，请检查 EMAIL_CONFIG 的值。")
                    raise
            else:
                print("没有配置 EMAIL_CONFIG 环境变量，请设置邮箱相关配置。")
                raise ValueError("缺少邮箱配置")
        self.notifier = get_notifier(notifier_type, config)



    # iOS 端登录
    # iOS 端登录（修正email字段为手机号）
    def ios_login(self, phone, password):
        """
        iOS 端手机号登录（兼容接口email字段要求）

        :param phone: 手机号（作为登录账号传入email字段）
        :param password: 密码
        :return: 登录结果
        """
        login_url = "https://floor.huluxia.com/account/login/IOS/1.0"
        headers = {
            "Accept": "*/*",
            "Connection": "keep-alive",
            "Accept-Encoding": "gzip, deflate, br",
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "Floor/1.2.2 (iPhone; iOS 18.2; Scale/3.00)",
            "Host": "floor.huluxia.com"
        }
        login_data = {
            "access_token": "",
            "app_version": "1.2.2",
            "code": "",
            "device_code": device_code,
            "device_model": "iPhone14%2C3",
            "phone": "",  # 保持phone字段为空（根据接口要求）
            "market_id": "floor_huluxia",
            "openid": "",
            "password": self.md5(password),
            "email": phone,  # 关键修改：将手机号传入email字段
            "platform": "1"
        }
        login_res = session.post(url=login_url, data=login_data, headers=headers)
        #print("登录结果：", login_res.json())  # 调试用，测试通过后可删除
        return login_res.json()

    # 登录后设置相关信息（改为手机号登录）
    def set_config(self, phone, password):  # 修改参数名：email -> phone
        """
        手机号登录后设置相关信息

        :param phone: 手机号
        :param password: 密码
        :return: 返回登录后生成的key值
        """
        data = self.ios_login(phone, password)  # 传递手机号参数
        status = data['status']
        if status == 0:
            self.notifier.send("手机号或密码错误!")  # 更新错误提示
        else:
            self._key = data['_key']
            self.userid = data['user']['userID']
            return self._key

    # 获取用户信息
    def user_info(self):
        """

        :return: 返回用户的昵称、等级、当前经验值以及下一等级的经验值
        """
        get_info_url = 'http://floor.huluxia.com/user/info/ANDROID/4.1.8?' \
                       'platform=' + platform + \
                       '&gkey=' + gkey + \
                       '&app_version=' + app_version + \
                       '&versioncode=' + versioncode + \
                       '&market_id=' + market_id + \
                       '&_key=' + self._key + \
                       '&device_code=' + device_code + \
                       '&phone_brand_type=' + phone_brand_type + \
                       '&user_id=' + str(self.userid)
        get_info_res = requests.get(url=get_info_url, headers=headers).json()
        nick = get_info_res.get('nick', '未知')
        level = get_info_res.get('level', 0)
        exp = get_info_res.get('exp', 0)
        next_exp = get_info_res.get('nextExp', 0)
        return nick, level, exp, next_exp

    # md5加密
    def md5(self, text: str) -> str:
        """

        :param text: 需要进行md5加密的文本内容
        :return: 加密后的内容
        """
        _md5 = hashlib.md5()
        _md5.update(text.encode())
        return _md5.hexdigest()

    # 时间戳
    def timestamp(self) -> int:
        # 原 int(round(time.time() * 1000)) 易出现参数错误
        return int(time.time())

    # sign 葫芦侠三楼签到用到的特殊签名
    def sign_get(self) -> str:
        """
        生成签到签名

        :return: 签到签名
        """
        n = self.cat_id
        i = str(self.timestamp())
        r = 'fa1c28a5b62e79c3e63d9030b6142e4b'
        result = "cat_id" + n + "time" + i + r
        c = self.md5(result)  # sign的构成：板块id + 时间戳 + 固定字符
        return c

    # 签到（改为手机号登录）
    def huluxia_signin(self, phone, password):  # 修改参数名：email -> phone
        """
        葫芦侠三楼签到（手机号登录版）

        :param phone: 手机号
        :param password: 密码
        :return: 签到结果
        """
        # 发送开始签到的通知（修改时间获取逻辑）
        # 获取UTC时间并加8小时得到北京时间（自动处理日期进位，无需手动减24）
        utc_now = datetime.now(timezone.utc)
        beijing_time = utc_now + timedelta(hours=8)  # 加8小时
        start_msg = f"📢 葫芦侠三楼开始签到啦！开始时间（北京时间）：{beijing_time.strftime('%Y-%m-%d %H:%M:%S')}"
        notifier_type = os.getenv("NOTIFIER_TYPE")
        if notifier_type == "wechat":
            self.notifier.send(start_msg)

        # 初始化通知信息
        self.set_config(phone, password)  # 传递手机号参数
        info = self.user_info()
        logger.info(f'正在为{info[0]}签到\n等级：Lv.{info[1]}\n经验值：{info[2]}/{info[3]}')

        # 获取通知类型
        print("通知类型：", notifier_type)

        total_exp = 0  # 记录总共获取的经验值
        success_count = 0  # 成功签到的板块数
        fail_count = 0  # 失败签到的板块数
        failed_plates = []  # 失败的板块名称

        # 循环签到每个版块
        for ct in cat_id_dict.keys():
            self.cat_id = ct
            sign = self.sign_get().upper()
            signin_url = (
                f"http://floor.huluxia.com/user/signin/ANDROID/4.1.8?"
                f"platform={platform}&gkey={gkey}&app_version={app_version}&versioncode={versioncode}"
                f"&market_id={market_id}&_key={self._key}&device_code={device_code}"
                f"&phone_brand_type={phone_brand_type}&cat_id={self.cat_id}&time={self.timestamp()}"
            )
            post_data = {"sign": sign}
            try:
                signin_res = session.post(url=signin_url, headers=headers, data=post_data).json()
            except Exception as e:
                fail_count += 1
                failed_plates.append(cat_id_dict[self.cat_id])
                logger.error(f"签到过程中出现错误：{e}")
                continue

            # 处理签到结果
            if signin_res.get('status') == 0:
                fail_count += 1
                failed_plates.append(cat_id_dict[self.cat_id])
                logger.warning(f'【{cat_id_dict[self.cat_id]}】签到失败，请手动签到。')
                continue

            # 签到成功，记录经验值
            signin_exp = signin_res.get('experienceVal', 0)
            self.signin_continue_days = signin_res.get('continueDays', 0)
            success_count += 1
            total_exp += signin_exp
            logger.info(f'【{cat_id_dict[self.cat_id]}】签到成功，经验值 +{signin_exp}')
            time.sleep(3)

        # 汇总签到结果
        summary_msg = [
            f'用户：{info[0]}',
            f'总签到板块：{len(cat_id_dict)}',
            f'成功：{success_count}',
            f'失败：{fail_count}',
            f'共获得：{total_exp} 经验值'
        ]

        if failed_plates:
            summary_msg.append(f'失败板块：{", ".join(failed_plates)}')

        # 完成签到后的用户信息
        final_info = self.user_info()
        final_msg = [
            f'当前等级：Lv.{final_info[1]}',
            f'当前经验值：{final_info[2]}/{final_info[3]}',
            f'已连续签到：{self.signin_continue_days} 天',
            f'预计还需签到：{(int(final_info[3]) - int(final_info[2])) // total_exp + 1 if total_exp else "未知"} 天'
        ]

        # 合并所有需要推送的消息
        notification_msg = "\n\n".join([
            "📜 葫芦侠三楼签到汇总",
            "----------------",
            "\n".join(summary_msg),
            "----------------",
            "\n".join(final_msg),
            "----------------",
            "🎉 签到任务已完成！"
        ])

        # 发送通知
        if notifier_type in ["wechat", "email"]:
            self.notifier.send(notification_msg)
