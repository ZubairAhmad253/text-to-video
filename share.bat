@echo off
rem Give the running site (run.bat) a public https link using a free Cloudflare quick tunnel.
rem The link is printed below (https://....trycloudflare.com) and changes every time you start this.
cd /d "%~dp0"
where cloudflared >nul 2>nul && (set CF=cloudflared) || (set CF="C:\Program Files (x86)\cloudflared\cloudflared.exe")
echo Starting a public link for http://localhost:8000 ...
echo Look for the line with https://....trycloudflare.com below. Close this window to stop sharing.
echo.
rem use an empty config so rules in %USERPROFILE%\.cloudflared\config.yml (other tunnels) don't apply
type nul > "%TEMP%\photo-to-video-tunnel.yml"
%CF% tunnel --config "%TEMP%\photo-to-video-tunnel.yml" --no-autoupdate --url http://localhost:8000
pause
