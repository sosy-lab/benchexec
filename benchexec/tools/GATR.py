# Módulo de información de herramienta para BenchExec (SV-COMP)
import benchexec.result as result
import benchexec.tools.template

class Tool(benchexec.tools.template.BaseTool2):
    """
    Módulo de integración para GATR v3 software verifier
    """

    def executable(self, tool_locator):
        # Busca el ejecutable run_TRACK dentro de tu carpeta bin
        return tool_locator.find_executable("run_TRACK", subdir="bin")

    def name(self):
        return "GATR Solver"

    def version(self, executable):
        # Ejecuta run_TRACK --version para el sistema automático
        return self._version_from_tool(executable, arg="--version")

    def determine_result(self, run):
        # Interpreta las salidas de texto de tu herramienta para clasificar el resultado
        output = run.output
        if not output:
            return result.RESULT_UNKNOWN
            
        # Analiza las últimas líneas buscando los estados estándar de la competencia
        for line in reversed(output):
            if "TRUE" in line:
                return result.RESULT_TRUE_PROP
            elif "FALSE" in line:
                return result.RESULT_FALSE_PROP
                
        return result.RESULT_UNKNOWN
