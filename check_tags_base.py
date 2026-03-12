import re
import os

def check_div_balance(filename):
    if not os.path.exists(filename):
        print(f"File not found: {filename}")
        return
        
    with open(filename, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Remove everything between {% %} and {{ }} to avoid confusing the parser
    content = re.sub(r'\{%.*?%\}', '', content, flags=re.DOTALL)
    content = re.sub(r'\{\{.*?\}\}', '', content, flags=re.DOTALL)
    content = re.sub(r'<!--.*?-->', '', content, flags=re.DOTALL)
    content = re.sub(r'<script.*?>.*?</script>', '', content, flags=re.DOTALL)
    content = re.sub(r'<style.*?>.*?</style>', '', content, flags=re.DOTALL)
    
    stack = []
    lines = content.split('\n')
    for i, line in enumerate(lines, 1):
        # Find all divs (simplified regex)
        tags = re.findall(r'<(div|/div)[^>]*>', line)
        for tag in tags:
            if tag == 'div':
                stack.append(i)
            else:
                if not stack:
                    print(f"Error: spare </div> at line {i}")
                else:
                    stack.pop()
    
    if stack:
        print(f"Error: {len(stack)} unclosed <div> tags started at lines: {stack}")
    else:
        print(f"Balance in {filename} is OK.")

check_div_balance(r'C:\Users\bogat\Downloads\SMFitness\templates\base.html')
