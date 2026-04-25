-- run_fresh_start_test.applescript
-- Opens Terminal.app and runs the fresh start test from an external visible terminal

set scriptPath to "/Users/busiji/workbot/skills/tmux-skills/scripts/test_fresh_start.sh"
set logPath to "/tmp/tmux-fresh-start-applescript-" & (do shell script "date +%Y%m%d-%H%M%S") & ".log"
set commandText to "echo " & quoted form of "=== Fresh Start Test via AppleScript ===" & " && " & ¬
	"bash " & quoted form of scriptPath & " 2>&1 | tee " & quoted form of logPath & "; " & ¬
	"echo ''; echo " & quoted form of ("Test completed. Log saved to: " & logPath) & " && " & ¬
	"echo " & quoted form of "Press any key to close this window..." & " && read -n 1"

tell application "Terminal"
	activate
	do script commandText
end tell
