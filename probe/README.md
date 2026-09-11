# 확인용 스크립트

애드온을 만들면서 블렌더에 직접 물어본 것들이다. 블렌더 판이 올라갔을 때 다시 돌려 보려고 남겨 둔다.
전부 블렌더를 띄워야 돌아간다.

| 파일 | 하는 일 | 창이 필요한가 |
|---|---|---|
| `check_api.py` | 애드온이 기대는 블렌더 성질이 그대로 있는지 본다. 종료 코드 0 이면 깨끗하다 | 아니다 |
| `find_free_key.py` | 팝업 단축키로 쓸 수 있는, 겹치지 않는 조합을 찾는다 | 그렇다 |
| `gui_shot.py` | 팝업을 실제로 띄우고 화면을 찍는다 | 그렇다 |

```bash
BL=/Applications/Blender.app/Contents/MacOS/Blender

# 창 없이
$BL --background --python probe/check_api.py

# 창을 띄워야 하는 것들 (단축키와 팝업 모양은 창이 있어야만 확인된다)
$BL --factory-startup --python probe/find_free_key.py
GUIDE_SHOT_MODE=search $BL --factory-startup --python probe/gui_shot.py
GUIDE_SHOT_MODE=edit   $BL --factory-startup --python probe/gui_shot.py
```

⚠️ **단축키는 창 없이 띄우면 읽히지 않는다.** 창 없는 블렌더에서는 키맵 항목이 2개뿐이고,
창을 띄우면 967개가 나온다. 그래서 단축키가 제대로 나오는지는 `gui_shot.py` 로만 확인할 수 있다.

⚠️ **타이머 안에서 `bpy.ops.wm.read_homefile()` 을 부르면 안 된다.** 예약해 둔 다음 단계까지
같이 지워져서 스크립트가 그 자리에 멈추고 블렌더가 안 닫힌다. 실제로 한 번 겪었다.
