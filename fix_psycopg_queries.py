#!/usr/bin/env python3
"""
Script to convert psycopg3 queries to psycopg2 queries in the Flask app.
"""

import re

def fix_psycopg_queries():
    """Convert psycopg3 syntax to psycopg2 syntax."""
    
    with open('web/app_with_database_psycopg3.py', 'r') as f:
        content = f.read()
    
    # Pattern to match conn.execute() calls with .fetchall() or .fetchone()
    pattern = r'(\s+)(results? = )?conn\.execute\("""\n(.*?)\n\s*"""\)\.(fetchall|fetchone)\(\)'
    
    def replace_query(match):
        indent = match.group(1)
        var_assign = match.group(2) or ""
        query = match.group(3)
        fetch_method = match.group(4)
        
        # Add cursor creation and cleanup
        result = f"""{indent}cursor = conn.cursor()
{indent}cursor.execute(\"\"\"
{query}
{indent}\"\"\")
{indent}{var_assign}results = cursor.{fetch_method}()
{indent}cursor.close()"""
        
        return result
    
    # Apply the replacement
    new_content = re.sub(pattern, replace_query, content, flags=re.DOTALL)
    
    # Handle single-line queries
    single_line_pattern = r'(\s+)(results? = )?conn\.execute\("([^"]+)"\)\.(fetchall|fetchone)\(\)'
    
    def replace_single_query(match):
        indent = match.group(1)
        var_assign = match.group(2) or ""
        query = match.group(3)
        fetch_method = match.group(4)
        
        result = f"""{indent}cursor = conn.cursor()
{indent}cursor.execute("{query}")
{indent}{var_assign}results = cursor.{fetch_method}()
{indent}cursor.close()"""
        
        return result
    
    new_content = re.sub(single_line_pattern, replace_single_query, new_content)
    
    # Write the fixed content
    with open('web/app_with_database_psycopg3.py', 'w') as f:
        f.write(new_content)
    
    print("✅ Converted psycopg3 queries to psycopg2 syntax")

if __name__ == "__main__":
    fix_psycopg_queries()
