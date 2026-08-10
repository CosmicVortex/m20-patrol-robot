#!/usr/bin/env python3
"""
RTSP 视频流预览
用法: python preview_rtsp.py [rtsp_url]

依赖: opencv-python
"""

import argparse
import sys
import time
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
from rtsp_client import read_rtsp_stream

try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False

DEFAULT_URL = "rtsp://192.168.1.108:554/id=1&type=0"
# DEFAULT_URL = "rtsp://10.200.22.33:554/id=1&type=0"


def preview_rtsp(url: str, transport: Optional[str] = "tcp", low_latency: bool = False) -> int:
    """使用 OpenCV 预览 RTSP 视频流"""
    if not HAS_CV2:
        print("需要安装 opencv-python: pip install opencv-python")
        return 1

    print(f"连接: {url}" + (" [低延迟]" if low_latency else ""))
    print("按 'q' 退出 | 's' 保存快照")

    try:
        cv2.namedWindow("RTSP Stream", cv2.WINDOW_NORMAL)
        cv2.resizeWindow("RTSP Stream", 960, 540)

        for ret, frame in read_rtsp_stream(url, transport=transport, low_latency=low_latency):
            if not ret or frame is None:
                print("读取帧失败或流结束")
                break

            cv2.imshow("RTSP Stream", frame)
            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break
            elif key == ord("s"):
                filename = f"snapshot_{time.strftime('%Y%m%d_%H%M%S')}.jpg"
                cv2.imwrite(filename, frame)
                print(f"快照保存为: {filename}")

    except KeyboardInterrupt:
        print("\n用户中断")
    except RuntimeError as e:
        print(f"错误: {e}")
        return 1
    finally:
        cv2.destroyAllWindows()
    return 0


def main():
    parser = argparse.ArgumentParser(description="RTSP 视频流预览")
    parser.add_argument("url", nargs="?", default=DEFAULT_URL, help=f"RTSP 地址 (默认: {DEFAULT_URL})")
    parser.add_argument("-t", "--transport", choices=["tcp", "udp", "none"], default="tcp",
                        help="传输方式 (默认: tcp)")
    parser.add_argument("-l", "--low-latency", action="store_true",
                        help="低延迟模式（减少缓冲，缩短延迟）")
    args = parser.parse_args()
    tr = None if args.transport == "none" else args.transport
    sys.exit(preview_rtsp(args.url, transport=tr, low_latency=args.low_latency))


if __name__ == "__main__":
    main()
