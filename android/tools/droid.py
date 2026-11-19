"""Drive the LogoSphere app on a USB-connected phone over adb, for manual test
runs. Compose semantics show up in `uiautomator dump`, so elements are found by
their text or content description.

  python droid.py tap "<text>" [index]   tap the element whose text/content-desc matches <text>
  python droid.py texts                  list visible labels with their centres
  python droid.py raw [y_from y_to]      every node in a band, labelled or not
  python droid.py type "<text>"          type into the focused field
  python droid.py shot <name>            screenshot to shots/<name>.png
  python droid.py back | swipe-up | swipe-down

Coordinates suit a 1080x2220 screen. Hide the keyboard with `back`, not
KEYCODE_ESCAPE (that acts as Back in the app and can close it).
"""
import os
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

ADB = (os.environ.get('ADB') or shutil.which('adb') or os.path.join(
    os.environ.get('ANDROID_HOME') or os.path.expanduser('~/AppData/Local/Android/Sdk'),
    'platform-tools', 'adb'))
HERE = os.path.dirname(os.path.abspath(__file__))


def adb(*args, binary=False):
    out = subprocess.run([ADB, *args], capture_output=True)
    return out.stdout if binary else out.stdout.decode('utf-8', 'replace')


def nodes():
    adb('shell', 'uiautomator', 'dump', '/sdcard/ui.xml')
    xml = adb('shell', 'cat', '/sdcard/ui.xml')
    xml = xml[xml.find('<?xml'):]
    root = ET.fromstring(xml)
    found = []
    for n in root.iter('node'):
        label = (n.get('text') or '') or (n.get('content-desc') or '')
        m = re.match(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', n.get('bounds', ''))
        if label and m:
            x1, y1, x2, y2 = map(int, m.groups())
            found.append((label, (x1 + x2) // 2, (y1 + y2) // 2))
    return found


def main(argv):
    sys.stdout.reconfigure(encoding='utf-8')
    if len(argv) < 2:
        print(__doc__)
        return 2
    cmd = argv[1]
    if cmd == 'tap':
        want, index = argv[2].lower(), int(argv[3]) if len(argv) > 3 else 0
        all_nodes = nodes()
        # Exact labels first ("Openings" the tab, not "My openings").
        matches = [n for n in all_nodes if n[0].lower() == want] or [n for n in all_nodes if want in n[0].lower()]
        if len(matches) <= index:
            print(f'not found: {argv[2]!r}')
            return 1
        label, x, y = matches[index]
        adb('shell', 'input', 'tap', str(x), str(y))
        print(f'tapped {label!r} at {x},{y}')
    elif cmd == 'texts':
        for label, x, y in nodes():
            print(f'{x:5d},{y:5d}  {label}')
    elif cmd == 'shot':
        os.makedirs(os.path.join(HERE, 'shots'), exist_ok=True)
        path = os.path.join(HERE, 'shots', argv[2] + '.png')
        with open(path, 'wb') as fh:
            fh.write(adb('exec-out', 'screencap', '-p', binary=True))
        print(path)
    elif cmd == 'type':
        # adb's `input text` needs spaces as %s and shell metacharacters escaped.
        text = argv[2]
        for ch in '\\"\'()&<>;|*~`$!?#':
            text = text.replace(ch, '\\' + ch)
        adb('shell', 'input', 'text', text.replace(' ', '%s'))
        print(f'typed {argv[2]!r}')
    elif cmd == 'raw':
        # Every node in a y range, labelled or not: raw [y_from y_to]
        lo, hi = (int(argv[2]), int(argv[3])) if len(argv) > 3 else (0, 99999)
        adb('shell', 'uiautomator', 'dump', '/sdcard/ui.xml')
        xml = adb('shell', 'cat', '/sdcard/ui.xml')
        root = ET.fromstring(xml[xml.find('<?xml'):])
        for n in root.iter('node'):
            m = re.match(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', n.get('bounds', ''))
            if m and int(m.group(2)) >= lo and int(m.group(4)) <= hi:
                print(n.get('bounds'), repr(n.get('text')), repr(n.get('content-desc')),
                      n.get('class'), 'clickable' if n.get('clickable') == 'true' else '')
    elif cmd == 'back':
        adb('shell', 'input', 'keyevent', 'KEYCODE_BACK')
    elif cmd == 'swipe-up':
        adb('shell', 'input', 'swipe', '540', '1700', '540', '700', '300')
    elif cmd == 'swipe-down':
        adb('shell', 'input', 'swipe', '540', '700', '540', '1700', '300')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
