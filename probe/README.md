# 확인용 스크립트

애드온을 만들면서 블렌더에 직접 물어본 것들이다. 블렌더 판이 올라갔을 때 다시 돌려 보려고 남겨 둔다.
전부 블렌더를 띄워야 돌아간다.

| 파일 | 하는 일 | 창이 필요한가 |
|---|---|---|
| `check_api.py` | 애드온이 기대는 블렌더 성질이 그대로 있는지 본다. 종료 코드 0 이면 깨끗하다 | 아니다 |
| `find_free_key.py` | 팝업 단축키로 쓸 수 있는, 겹치지 않는 조합을 찾는다 | 그렇다 |
| `gui_shot.py` | 팝업을 실제로 띄우고 화면을 찍는다 | 그렇다 |
| `check_focus.py` | 안내 기능이 실제 창에서 도는지 본다. 그리기 손잡이 · 강조 오버레이 · 모드 바꾸기를 모두 확인한다 | 그렇다 |
| `check_agent.py` | 에이전트에게 실제로 물어보고 답이 돌아오는지 본다. ⚠️ 바깥 프로그램을 실행한다 | 그렇다 |
| `check_click.py` | 팝업 안의 단추가 첫 클릭에 닿는지 본다. 이벤트를 흉내 내어 실제로 누른다 | 그렇다 |
| `check_catalog_ui.py` | 검색 결과 목록이 실제 팝업에서 도는지 본다. 카탈로그·설정값·음차·사용 방법을 모두 확인한다 | 그렇다 |
| `build_catalog.py` | 점검이 아니라 만드는 스크립트다. `catalog_ko.json` 을 새로 쓴다 | 아니다 |

```bash
BL=/Applications/Blender.app/Contents/MacOS/Blender

# 창 없이
$BL --background --python probe/check_api.py

# 창을 띄워야 하는 것들 (단축키와 팝업 모양은 창이 있어야만 확인된다)
$BL --factory-startup --python probe/find_free_key.py
GUIDE_SHOT_MODE=search $BL --factory-startup --python probe/gui_shot.py
GUIDE_SHOT_MODE=edit   $BL --factory-startup --python probe/gui_shot.py

# 안내 기능 점검. GUIDE_FOCUS_SHOT=1 을 붙이면 강조 표시를 찍은 화면도 남는다.
$BL --factory-startup --python probe/check_focus.py
GUIDE_FOCUS_SHOT=1 $BL --factory-startup --python probe/check_focus.py

# 에이전트 점검. ⚠️ 바깥 프로그램을 실제로 실행한다.
$BL --python probe/check_agent.py

# 검색 결과 목록 점검
$BL --factory-startup --python probe/check_catalog_ui.py

# 카탈로그를 다시 만든다. 블렌더 판이 올라갔을 때 돌린다.
$BL --background --factory-startup --python probe/build_catalog.py

# 팝업 첫 클릭 점검. 조건마다 따로 띄워야 한다.
for c in none plain focus; do
  GUIDE_CLICK_CASE=$c $BL --factory-startup --enable-event-simulate \
      --python probe/check_click.py
done
```

⚠️ **단축키는 창 없이 띄우면 읽히지 않는다.** 창 없는 블렌더에서는 키맵 항목이 2개뿐이고,
창을 띄우면 967개가 나온다. 그래서 단축키가 제대로 나오는지는 `gui_shot.py` 로만 확인할 수 있다.

⚠️ **오버레이와 모드 바꾸기도 창이 있어야만 확인된다.** 창 없이 띄운 블렌더에는 gpu 문맥이
없어서 그리기 손잡이가 아예 걸리지 않고, `bpy.ops.object.mode_set` 도 부를 자리가 없다.
그래서 `test_headless.py` 는 안내 기능을 한 줄도 확인하지 못한다. `check_focus.py` 가 그 자리를 맡는다.

⚠️ **`screen.screenshot` 은 팝업과 모달 오버레이를 담지 못한다.** 블렌더가 화면을 다시 그려서
찍기 때문에, 그때는 팝업도 변형 중의 점선 안내선도 없다. 그래서 그런 것들은 화면으로 확인할 수
없고 값으로 재는 수밖에 없다. 등록된 그리기 손잡이가 그리는 것(우리 강조 오버레이)은 찍힌다.

⚠️ **시작 화면이 떠 있으면 팝업이 안 열린다.** `--factory-startup` 만 주고 띄우면 시작 화면이
남아서 단축키를 눌러도 팝업이 안 뜬다. `check_click.py` 는 먼저 `read_homefile` 로 치운다.

⚠️ **이벤트 흉내는 창이 다 뜬 뒤에야 붙는다.** 스크립트를 읽는 시점에 `Window.event_simulate`
유무를 확인하면 아직 없어서 잘못 판단한다. 타이머 안에서 확인해야 한다.

⚠️ **바깥 프로그램을 부를 때 `stdin` 을 막아야 한다.** 막지 않으면 부른 프로그램이
블렌더의 입력을 물려받아 기다린다. `claude` 는 3초를 기다린 뒤 경고를 내고 진행하는데,
그 사이에 답이 비어서 돌아왔다. `stdin=subprocess.DEVNULL` 로 막는다.

⚠️ **`hasattr(bpy.ops.…)` 로는 오퍼레이터 등록 여부를 알 수 없다.** `bpy.ops` 는 없는 이름에도
껍데기를 돌려주므로 언제나 참이다. `bpy.types` 로 찾는 것도 안 된다. 블렌더가 `bl_idname` 에서
만드는 이름은 `BLENDER_GUIDE_OT_focus` 처럼 밑줄이 더 붙어서 클래스 이름과 다르다.
`poll()` 을 불러 보면 없는 오퍼레이터일 때만 `AttributeError` 가 난다.

⚠️ **이미 등록된 오퍼레이터의 메서드를 파이썬에서 갈아 끼우면 블렌더가 죽는다.** 점검하려고
`execute` 를 바꿔치기했다가 겪었다. 점검 전용 오퍼레이터를 따로 등록해서 써야 한다.

⚠️ **타이머 안에서 `bpy.ops.wm.read_homefile()` 을 부르면 안 된다.** 예약해 둔 다음 단계까지
같이 지워져서 스크립트가 그 자리에 멈추고 블렌더가 안 닫힌다. 실제로 한 번 겪었다.
꼭 불러야 한다면 부른 **뒤에** 다음 단계를 등록한다. `check_click.py` 가 그렇게 한다.
