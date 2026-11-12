# Prints non-ASCII text, used to check the runner does not crash on a GBK/cp1252 console.
import sys
sys.stdin.read()
print("答案 réponse ответ")
