import os

bashrc = "/home/hadoop/.bashrc"
with open(bashrc) as f:
    lines = f.readlines()

# Remove bad env vars (last 6 lines)
while lines and not lines[-1].startswith('export JAVA_HOME'):
    lines.pop()
# Remove until we hit the fi line before our additions
while lines and lines[-1].strip() == '' or lines[-1].strip() == 'fi':
    if lines[-1].strip() == 'fi':
        break
    lines.pop()

# Remove the fi line if it's right before our bad additions
if lines and lines[-1].strip() == 'fi':
    pass  # keep fi

# Remove trailing empty lines
while lines and lines[-1].strip() == '':
    lines.pop()

# Now remove any lines that look like our bad env vars
new_lines = []
skip = False
for line in lines:
    if line.strip() == 'fi' and not skip:
        new_lines.append(line)
        skip = True
        continue
    if skip and (line.startswith('export JAVA_HOME') or line.startswith('export PATH') or line.startswith('export HADOOP_HOME')):
        continue
    new_lines.append(line)

# Remove trailing empty lines again
while new_lines and new_lines[-1].strip() == '':
    new_lines.pop()

# Add proper env vars
new_lines.append('\n')
new_lines.append('export JAVA_HOME=/usr/lib/jvm/java-8-openjdk-amd64\n')
new_lines.append('export PATH=$PATH:$JAVA_HOME/bin\n')
new_lines.append('export HADOOP_HOME=/opt/module/hadoop-3.3.6\n')
new_lines.append('export PATH=$PATH:$HADOOP_HOME/bin:$HADOOP_HOME/sbin\n')

with open(bashrc, 'w') as f:
    f.writelines(new_lines)

print("bashrc updated successfully")
