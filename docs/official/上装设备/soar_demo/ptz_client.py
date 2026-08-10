#!/usr/bin/env python3
"""
云台控制接口 - 基于数尔安防 WEB2.0 通讯协议
支持 CMS_PTZ_TYPE 枚举中的全部云台控制功能。
自动登录、定时心跳保活（Heartbeat.cgi）。

依赖: pip install requests

协议参考: 1.WEB 通讯协议 - 数尔安防.pdf 第 7 节、第 26 节

用法:
    from ptz_client import PtzClient, CMS_PTZ_TYPE, MerlinSession

    # 推荐：自动登录 + 每 10 秒心跳
    client = PtzClient("http://192.168.1.108", "admin", "123456")
    client.up(speed=5)
    client.goto_preset(1)
    client.close()  # 停止心跳

    # 或使用 with
    with PtzClient("http://192.168.1.108", "admin", "123456") as client:
        client.up(speed=5)
"""

import base64
import logging
import threading
from time import sleep
from enum import IntEnum
from typing import Optional
import requests
import os
# 强制禁用代理
os.environ['no_proxy'] = '*'

logger = logging.getLogger(__name__)

# 终端红色输出（状态码非 200 时使用）
RED = "\033[31m"
RESET = "\033[0m"

__all__ = ["PtzClient", "CMS_PTZ_TYPE", "MerlinSession"]


class MerlinSession:
    """
    数尔安防 WEB2.0 会话管理：自动登录、定时心跳保活。
    协议 26：HTTP 短连接会话管理。
    """

    def __init__(
        self,
        base_url: str = "http://192.168.1.108",
        username: str = "admin",
        password: str = "123456",
        path_prefix: str = "/merlin",
        timeout: float = 5.0,
        heartbeat_interval: float = 10.0,
        debug: bool = True,
    ):
        """
        Args:
            base_url: 设备地址
            username: 用户名
            password: 密码
            path_prefix: API 路径前缀
            timeout: 请求超时
            heartbeat_interval: 心跳间隔（秒），应小于 session_expires
            debug: 是否打印请求日志
        """
        self.debug = debug
        self.base_url = base_url.rstrip("/")
        self.path_prefix = path_prefix.rstrip("/") or "/merlin"
        self.timeout = timeout
        self.heartbeat_interval = heartbeat_interval
        self._auth = base64.b64encode(f"{username}:{password}".encode()).decode()
        self._session: Optional[str] = None
        self._lock = threading.RLock()  # 可重入锁，避免 post()->login() 内再次获取时死锁
        self._heartbeat_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def _get_headers(self, use_session: bool = True) -> dict:
        h = {
            "Authorization": f"Basic {self._auth}",
            "Agent": "merlin HTTP agent",
            "Accept": "application/json, text/plain, */*",
            "Connection": "keep-alive",
            "Content-Type": "application/json",
        }
        if use_session and self._session:
            h["Session"] = self._session
        return h

    def _log(self, msg: str, *args) -> None:
        if self.debug:
            logger.info(msg, *args)

    def _log_red(self, msg: str, *args) -> None:
        """状态码非 200 时红色打印"""
        if self.debug:
            full_msg = msg % args if args else msg
            logger.error("%s%s%s", RED, full_msg, RESET)

    def login(self) -> bool:
        """登录获取 Session（协议 26.2）"""
        url = f"{self.base_url}{self.path_prefix}/Login.cgi?Type=WEB&Expires=30"
        self._log("[请求] GET %s", url)
        try:
            r = requests.get(url, headers=self._get_headers(use_session=False), timeout=self.timeout, verify=False)
            if r.status_code != 200:
                self._log_red("[响应] Login %s %s %.2fs", r.status_code, r.reason, r.elapsed.total_seconds())
                self._log_red("[响应] body: %s", r.text[:200] if r.text else "(empty)")
            else:
                self._log("[响应] Login %s %s %.2fs", r.status_code, r.reason, r.elapsed.total_seconds())
            if r.status_code == 401:
                raise RuntimeError("登录失败: HTTP 401，请检查用户名和密码")
            if r.status_code != 200:
                return False
            data = r.json()
            session = data.get("Session") or (data.get("result") or {}).get("Session")
            with self._lock:
                self._session = str(session) if session else None
            self._log("[登录] Session=%s", (str(session)[:16] + "...") if session and len(str(session)) > 16 else session)
            return session is not None
        except Exception as e:
            self._log("[错误] Login %s: %s", type(e).__name__, e)
            with self._lock:
                self._session = None
            return False

    def _heartbeat_loop(self) -> None:
        """心跳循环（协议 26.4）"""
        while not self._stop_event.wait(timeout=self.heartbeat_interval):
            with self._lock:
                session = self._session
            if not session:
                continue
            self.heartbeat()

    def heartbeat(self) -> None:
        """发送心跳包"""
        url = f"{self.base_url}{self.path_prefix}/Heartbeat.cgi"
        try:
            r = requests.get(url, headers=self._get_headers(), timeout=self.timeout, verify=False)
            if r.status_code != 200:
                self._log_red("[心跳] %s %s，重新登录", r.status_code, r.reason)
                self.login()
            else:
                self._log("[心跳] %s %s %.2fs", r.status_code, r.reason, r.elapsed.total_seconds())
        except Exception as e:
            self._log("[心跳] 异常 %s: %s，重新登录", type(e).__name__, e)
            self.login()

    def start_heartbeat(self) -> None:
        """启动后台心跳线程"""
        self.heartbeat()
        if self._heartbeat_thread is not None and self._heartbeat_thread.is_alive():
            return
        self._stop_event.clear()
        self._heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self._heartbeat_thread.start()

    def stop_heartbeat(self) -> None:
        """停止心跳线程"""
        self._stop_event.set()
        if self._heartbeat_thread:
            self._heartbeat_thread.join(timeout=self.heartbeat_interval + 2)
            self._heartbeat_thread = None

    def close(self) -> None:
        """关闭会话，停止心跳"""
        self.stop_heartbeat()

    def __enter__(self) -> "MerlinSession":
        return self

    def __exit__(self, *args) -> None:
        self.close()

    def request(self, method: str, path: str, data: Optional[dict] = None, ensure_login: bool = True, use_session: Optional[bool] = None) -> requests.Response:
        """
        合并 GET 和 POST 请求，自动登录并携带 Session，可通过 use_session 控制是否带 Session。

        Args:
            method: 请求方式 'GET' 或 'POST'
            path: 路径，如 PtzCtrl.cgi（不含前缀）
            data: 请求数据(GET 用 params, POST 用 json)
            ensure_login: 若未登录则先登录
            use_session: 强制是否使用 Session（None 表示自动尝试，True/False强制控制）
        """
        if ensure_login:
            with self._lock:
                if not self._session:
                    self.login()
                    self.start_heartbeat()
        url = f"{self.base_url}{self.path_prefix}/{path}"
        if method.upper() == "GET":
            self._log("[请求] GET %s params=%s", url, data)
        else:
            self._log("[请求] POST %s body=%s", url, data)

        def _do_request(session_flag: bool) -> requests.Response:
            h = self._get_headers() if session_flag else self._get_headers(use_session=False)
            if method.upper() == "GET":
                return requests.get(url, headers=h, params=data, timeout=self.timeout, verify=False)
            elif method.upper() == "POST":
                return requests.post(url, headers=h, json=data, timeout=self.timeout, verify=False)
            else:
                raise ValueError(f"不支持的请求方法: {method}")

        try:
            if use_session is None:
                # 默认先尝试带session
                r = _do_request(session_flag=True)
            else:
                r = _do_request(session_flag=use_session)
            if r.status_code != 200:
                self._log_red("[响应] %s %s %s %s %.2fs", method.upper(), path, r.status_code, r.reason, r.elapsed.total_seconds())
                self._log_red("[响应] body: %s", r.text[:300] if r.text else "(empty)")
            else:
                self._log("[响应] %s %s %s %s %.2fs", method.upper(), path, r.status_code, r.reason, r.elapsed.total_seconds())
            return r
        except requests.exceptions.ConnectionError as e:
            err = str(e).lower()
            # 仅自动重试模式时，对session问题重试
            if (use_session is None) and self._session and ("closed" in err or "disconnected" in err or "without response" in err):
                self._log("[重试] 连接被关闭，尝试不带 Session")
                try:
                    r = _do_request(session_flag=False)
                    if r.status_code != 200:
                        self._log_red("[响应] %s %s %s %s %.2fs (无Session)", method.upper(), path, r.status_code, r.reason, r.elapsed.total_seconds())
                    else:
                        self._log("[响应] %s %s %s %s %.2fs (无Session)", method.upper(), path, r.status_code, r.reason, r.elapsed.total_seconds())
                    return r
                except Exception:
                    pass
            self._log("[错误] %s %s %s: %s", method.upper(), path, type(e).__name__, e)
            raise
        except Exception as e:
            self._log("[错误] %s %s %s: %s", method.upper(), path, type(e).__name__, e)
            raise

    def get(self, path: str, data: Optional[dict] = None, ensure_login: bool = True, use_session: Optional[bool] = None) -> requests.Response:
        """
        发送 GET 请求，自动登录并携带 Session。可通过 use_session 控制。
        """
        return self.request("GET", path, data=data, ensure_login=ensure_login, use_session=use_session)

    def post(self, path: str, data: Optional[dict] = None, ensure_login: bool = True, use_session: Optional[bool] = None) -> requests.Response:
        """
        发送 POST 请求，自动登录并携带 Session。可通过 use_session 控制。
        """
        return self.request("POST", path, data=data, ensure_login=ensure_login, use_session=use_session)

    def set_ptz_angle(
        self,
        yaw: float = 0,
        pitch: float = 0,
        roll: float = 0,
    ) -> requests.Response:
        """
        设置云台角度（SetPtzangle.cgi）。

        Args:
            yaw: 偏航角（度）
            pitch: 俯仰角（度）
            roll: 翻滚角（度）

        Returns:
            requests.Response
        """
        data = {"Angle": {"yaw": yaw, "pitch": pitch, "roll": roll}}
        return self.post("SetPtzangle.cgi", data=data, ensure_login=True)

    def set_ptz_ability(
        self,
        enable: int = 2,
    ) -> requests.Response:
        """
        设置云台使能（SetPtzAbility.cgi）。

        Args:
            enable: Motor.Enable 值，如 0关闭 1启动 2重启

        Returns:
            requests.Response
        """
        data = {"Motor": {"Enable": enable}}
        return self.post("SetPtzAbility.cgi", data=data, ensure_login=True)

    def set_ptz_direction(
        self,
        ptz_opt: str,
        speed: int = 20,
    ) -> requests.Response:
        """
        设置云台方向（SetPtzDirection.cgi）。
        Args:
            ptz_opt: 云台方向，如 "left-up"、"right-down"、"left-down"、"right-up"、"left"、"right"、"up"、"down"、"stop"
            speed: 速度，如 20
        """
        data = {"Direction": {"ptz_opt": ptz_opt, "speed": speed}}
        return self.post("SetPtzDirection.cgi", data=data, ensure_login=True)

    def set_ptz_control(
        self,
        operation: int,
        speed: int = 20,
        channelno: int = 0,
        value: int = 0,
    ) -> requests.Response:
        """
        设置云台控制（PtzCtrl.cgi）。
        Args:
            operation: 操作，如 9、10、0
                # CMS_PTZ_OPT_STOP = 0,//停止云台操作
                # CMS_PTZ_OPT_LEFTUP = 1,//左上
                # CMS_PTZ_OPT_UP = 2,//上
                # CMS_PTZ_OPT_RIGHTUP = 3,//右上
                # CMS_PTZ_OPT_LEFT = 4,//左
                # CMS_PTZ_OPT_RIGHT = 5,//右
                # //6 
                # CMS_PTZ_OPT_LEFTDOWN = 6,//左下
                # CMS_PTZ_OPT_DOWN = 7,//下
                # CMS_PTZ_OPT_RIGHTDOWN = 8,//右下
                # CMS_PTZ_OPT_ZOOM_WIDE = 9,//变倍+ 
                # CMS_PTZ_OPT_ZOOM_TELE = 10,//变倍-
                # //11 
                # CMS_PTZ_OPT_FOCUS_FAR = 11,//变焦+ 
                # CMS_PTZ_OPT_FOCUS_NEAR = 12,//变焦-
                # CMS_PTZ_OPT_IRIS_LARGE = 13,//光圈+ 
                # CMS_PTZ_OPT_IRIS_SMALL = 14,//光圈-
                # CMS_PTZ_OPT_GOTOPRESET = 20,//转到预置点
            speed: 速度，如 20
            channelno: 通道号，如 0
            value: 值，如 0
        """
        data = {"Operation": {"operation": operation, "speed": speed, "channelno": channelno, "value": value}}
        return self.get("PtzCtrl.cgi", data=data, ensure_login=True)

    def zoom_ctrl(self, zoom: int = 8, channelno: int = 0) -> requests.Response:
        """
        直接放大到指定倍率（ZoomCtrl.cgi）。

        Args:
            zoom: 变焦倍数，1-10
            channelno: 通道号，默认 0

        Returns:
            requests.Response
        """
        # 如果 zoom 超出 1-10 范围，则限制到范围内
        zoom = max(1, min(zoom, 10))
        data = {"zoom": zoom, "channelno": channelno}
        return self.get("ZoomCtrl.cgi", data=data, ensure_login=True)

    def get_fly_state_info(self) -> requests.Response:
        """
        获取飞行状态信息（GetFlyStateInfo.cgi）。

        Returns:
            requests.Response
        """
        return self.get("GetFlyStateInfo.cgi", ensure_login=True)


# 变焦
# http://192.168.1.108/merlin/PtzCtrl.cgi?operation=9&speed=5&channelno=0&value=0
# http://192.168.1.108/merlin/PtzCtrl.cgi?operation=10&speed=5&channelno=0&value=0
# http://192.168.1.108/merlin/PtzCtrl.cgi?operation=0&speed=5&channelno=0&value=0
# 控制云台
# http://192.168.1.108/merlin/SetPtzDirection.cgi?channel=0
# {
#     "Direction": {
#         "ptz_opt":"left",//stop, up, down, left, right, leftup, rightup, leftdown, rightdown, zoom_wide, zoom_tele, focus_far, focus_near, iris_large, iris_small
#         "speed": 5 //1-20
#     }
# }
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    # with MerlinSession() as client:
    # with MerlinSession(base_url="http://10.200.22.33") as client:
    with MerlinSession(base_url="http://192.168.1.108") as client:
        # client.set_ptz_direction(ptz_opt="left", speed=15)
        # sleep(3)
        # client.set_ptz_direction(ptz_opt="right", speed=15)
        # sleep(3)
        # client.set_ptz_direction(ptz_opt="up", speed=15)
        # sleep(3)
        # client.set_ptz_direction(ptz_opt="down", speed=15)
        # sleep(3)
        # client.set_ptz_direction(ptz_opt="stop", speed=15)
        # sleep(3)
        client.set_ptz_angle(yaw=180, pitch=0, roll=0)
        sleep(3)
        client.set_ptz_angle(yaw=0, pitch=0, roll=0)
        # 等待3秒后
        # 阻塞（暂停主线程，防止程序立即退出，让心跳线程持续运行）

        client.zoom_ctrl(zoom=3)
        resp = client.get_fly_state_info()
        print("get_fly_state_info 返回：", resp.text)
        sleep(5)
        client.zoom_ctrl(zoom=5)
        resp = client.get_fly_state_info()
        print("get_fly_state_info 返回：", resp.text)
        sleep(5)
        client.zoom_ctrl(zoom=1)
        resp = client.get_fly_state_info()
        print("get_fly_state_info 返回：", resp.text)
        input("按回车键退出...")