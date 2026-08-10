# P1-2: 暴露gimbal.connected属性

**问题**: handlers访问私有属性`_connected`

**文件1**: `backend/app/gimbal/adapter.py`

在`close()`方法后添加：
```python
@property
def connected(self) -> bool:
    """公开访问连接状态"""
    return self._connected
```

**文件2**: `backend/app/gimbal/handlers.py`

替换所有`gimbal._connected`为`gimbal.connected`：
```python
# 修改前
if not gimbal or not gimbal._connected:

# 修改后
if not gimbal or not gimbal.connected:
```

共需修改4处（GimbalStateHandler, GimbalMoveHandler, GimbalZoomHandler, GimbalAngleHandler）。

**验证**:
```python
from backend.app.gimbal.adapter import SoarGimbalAdapter

adapter = SoarGimbalAdapter()
assert adapter.connected == False

adapter._connected = True
assert adapter.connected == True
```
