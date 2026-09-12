# UI 설명 페이지

팝업이 어떻게 짜여 있는지를 한 장으로 보여 주는 페이지를 만든다.
팝업을 HTML 로 재현해 두고, 설명에 마우스를 올리면 해당 부분이 밝아진다.

```bash
BL=blender   # 자기 기기의 블렌더 자리

# ① 실제 화면을 찍는다 (블렌더 창이 필요하다)
GUIDE_SHOT_MODE=search $BL --factory-startup --python probe/gui_shot.py
GUIDE_SHOT_MODE=edit   $BL --factory-startup --python probe/gui_shot.py

# ② 페이지를 만든다
python3 docs/ui_page/build.py
```

만들어진 `out/index.html` 은 찍은 화면을 파일 안에 직접 담고 있어서,
어디로 옮겨도 그림이 같이 간다. 화면을 안 찍어도 페이지는 만들어지고 그림 자리만 빈다.

팝업이 마우스 자리에 뜨기 때문에 찍을 때마다 위치가 조금씩 달라진다.
잘린 그림이 이상하면 `build.py` 의 `CROPS` 값을 손본다.
