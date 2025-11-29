filename = 'outputs/dashboard_2025-11-29.html'
search_term = 'record_date'

try:
    with open(filename, 'r') as f:
        content = f.read()
        
    if search_term in content:
        print(f"Found '{search_term}' in {filename}")
        # Print context
        index = content.find(search_term)
        start = max(0, index - 50)
        end = min(len(content), index + 50)
        print(f"Context: ...{content[start:end]}...")
    else:
        print(f"'{search_term}' NOT found in {filename}")
        
    # Also check case insensitive
    if search_term.lower() in content.lower():
        print(f"Found '{search_term}' (case insensitive) in {filename}")
        
except Exception as e:
    print(f"Error: {e}")
