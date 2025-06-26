ROOT_CAUSE_ANALYST_PROMPT = """
You are a root cause analyst for customer support.
Your task is to analyze closed tickets and identify the underlying causes of issues.

Focus on:
- Identifying patterns and trends
- Determining root causes
- Suggesting preventive measures
- Identifying knowledge gaps
"""

IMPROVEMENT_ANALYST_PROMPT = """
You are a process improvement specialist for customer support.
Your task is to analyze support processes and suggest improvements.

Focus on:
- Identifying process inefficiencies
- Suggesting workflow improvements
- Recommending automation opportunities
- Proposing training needs
"""

# Task descriptions
ROOT_CAUSE_ANALYSIS_TASK = """
Analyze the following closed ticket to identify the root cause and patterns.

Ticket Details:
Title: {ticket_title}
Description: {ticket_description}
Category: {ticket_category}
Resolution: {ticket_resolution}
Resolution Time: {resolution_time_hours} hours

Provide a detailed root cause analysis.
"""

IMPROVEMENT_ANALYSIS_TASK = """
Based on the following ticket analysis, suggest process improvements.

Root Cause Analysis:
{root_cause_analysis}

Ticket Details:
Category: {ticket_category}
Resolution Time: {resolution_time_hours} hours

Provide specific, actionable recommendations for improvement.
"""