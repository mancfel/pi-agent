# Python Script Library Management Instructions

This document defines the guidelines that agents must follow when generating or using Python scripts within the project.

## Python Script Workflow

When an agent needs to generate or execute a Python script to perform an operation — whether explicitly requested by the user or autonomously determined by the model as necessary instead of creating a temporary inline script — it must strictly follow these steps:

1. **Preliminary check**:
   - Before writing a new script, the agent must determine whether the task is related to the execution of a skill requested by the user.
   - If a skill is involved, the agent must check the `scripts/` folder and `skill.md` inside that skill's directory (`skills/<skill-name>/`). Otherwise, the agent must check the global `scripts/` folder and `scripts/index.md`.
   - If the corresponding folder or index/documentation file does not exist yet, the agent must create them.
   - The agent must examine the index to check if a script useful for performing the task is already present.

2. **Case A: Existing script found**
   - If a suitable script is found, the agent must **execute** the existing script.
   - If necessary, the agent must **extend** the existing script to support the new use case.
   - The agent must update the script description inside `scripts/index.md` or `skill.md` to reflect the newly added features.

3. **Case B: No suitable script found**
   - If no suitable script exists, the agent must **create a new Python script** (saving it in the skill's `scripts/` folder if the user requested the execution of a skill, or otherwise in the global `scripts/` folder), designing it to be as **generic and reusable** as possible.
   - The agent must use the new script to perform the requested task.
   - The agent must add the new script to `scripts/index.md` or `skill.md`, including:
     - The script file name.
     - Instructions on how to use it (arguments, parameters, examples).
     - A detailed description of the features offered.

## Script Locations
	- **projectRoot\agent\scripts**
	- **~\.pi\agent\skills\<skill>\scripts**
	- **~\.pi\agent\scripts**