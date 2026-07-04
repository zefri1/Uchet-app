$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$VenvPython = Join-Path $Root ".venv\Scripts\python.exe"
$BuildDir = Join-Path $PSScriptRoot "build"
$DistDir = Join-Path $BuildDir "RealEstateUtilityApp"
$TemplatesDir = Join-Path $Root "app\templates"
$StaticDir = Join-Path $Root "app\static"
$AppIcon = Join-Path $PSScriptRoot "app_icon.ico"

if (!(Test-Path $VenvPython)) {
    throw "Virtual environment not found: $VenvPython"
}

if (Test-Path $BuildDir) {
    Remove-Item -LiteralPath $BuildDir -Recurse -Force
}

Push-Location $Root
try {
    & $VenvPython -m pip install -r requirements.txt
    & $VenvPython -c "from pathlib import Path; from PIL import Image, ImageDraw; icon_path = Path(r'''$AppIcon'''); size = 256; image = Image.new('RGBA', (size, size), '#1f4b99'); draw = ImageDraw.Draw(image); draw.rounded_rectangle((20, 20, size - 20, size - 20), radius=56, fill='#1f4b99', outline='#77c7ff', width=12); draw.rectangle((72, 72, 184, 212), fill='white'); draw.rectangle((96, 48, 160, 80), fill='#77c7ff'); [draw.rectangle((x, y, x + 16, y + 16), fill='#1f4b99') for y in (96, 128, 160) for x in (88, 120, 152)]; draw.rectangle((112, 176, 144, 212), fill='#1f4b99'); icon_path.parent.mkdir(parents=True, exist_ok=True); image.save(icon_path, format='ICO', sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])"
    & $VenvPython -m PyInstaller `
        --noconfirm `
        --clean `
        --distpath installer\build `
        --workpath installer\build-temp `
        installer\RealEstateUtilityApp.spec
}
finally {
    Pop-Location
}
