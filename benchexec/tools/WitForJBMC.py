import benchexec.tools.template
import benchexec.result as result


class Tool(benchexec.tools.template.BaseTool2):
 def executable(self, tool_locator):
  return tool_locator.find_executable("Wit4JBMC.py")
 def name(self):
  return "Wit4JBMC"
 def cmdline(self, executable, options, task, rlimits):
  return [executable] + options + list(task.input_files_or_identifier)
 def determine_result(self, run): 
  output = run.output
  validation = 'unknown'
  for line in output:
   if 'Exception' in line:
    if 'AssertionError' in line:
     validation = 'false'
    else:
     validation = 'unknown'
    break
   else:
    validation = 'true'

  if validation == 'false':
   status = result.RESULT_FALSE_PROP
  #print(exit_code)
  elif validation == 'true':
   status = result.RESULT_TRUE_PROP
  else:
   status = result.RESULT_UNKNOWN
  return status
