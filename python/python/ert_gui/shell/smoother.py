from ecl.util import BoolVector

from res.enkf import ESUpdate, ErtRunContext
from ert_gui.shell import assertConfigLoaded, ErtShellCollection
from ert_gui.shell.libshell import splitArguments, createFloatValidator
from res.enkf.enums import HookRuntime

class Smoother(ErtShellCollection):
    def __init__(self, parent):
        super(Smoother, self).__init__("smoother", parent)

        self.addShellProperty(name="overlap_alpha",
                              getter=Smoother.getOverlapAlpha,
                              setter=Smoother.setOverlapAlpha,
                              validator=createFloatValidator(),
                              completer=None,
                              help_arguments="[alpha_value]",
                              help_message="Show or set the overlap alpha.",
                              pretty_attribute="Overlap Alpha")

        self.addShellProperty(name="std_cutoff",
                              getter=Smoother.getStdCutOff,
                              setter=Smoother.setStdCutOff,
                              validator=createFloatValidator(minimum=0),
                              completer=None,
                              help_arguments="[cutoff_value]",
                              help_message="Show or set the standard deviation cutoff value (>0).",
                              pretty_attribute="Standard Deviation Cutoff")

        self.addShellProperty(name="global_std_scaling",
                              getter=Smoother.getGlobalStdScaling,
                              setter=Smoother.setGlobalStdScaling,
                              validator=createFloatValidator(minimum=0),
                              completer=None,
                              help_arguments="[std_scaling]",
                              help_message="Show or set the global standard deviation scaling value (>0) applied to updates.",
                              pretty_attribute="Global Standard Deviation Scaling")

        self.addShellFunction(name="update",
                              function=Smoother.update,
                              help_arguments="<variable_name> <value>",
                              help_message="Set a variable value.")


    @assertConfigLoaded
    def analysisConfig(self):
        """ @rtype: ert.analysis.AnalysisConfig """
        return self.ert().analysisConfig()

    def setOverlapAlpha(self, value):
        self.analysisConfig().setEnkfAlpha(value)

    def getOverlapAlpha(self):
        return self.analysisConfig().getEnkfAlpha()

    def setStdCutOff(self, value):
        self.analysisConfig().setStdCutoff(value)

    def getStdCutOff(self):
        return self.analysisConfig().getStdCutoff()

    def setGlobalStdScaling(self, value):
        self.analysisConfig().setGlobalStdScaling(value)

    def getGlobalStdScaling(self):
        return self.analysisConfig().getGlobalStdScaling()

    @assertConfigLoaded
    def update(self, line):
        arguments = splitArguments(line)

        if len(arguments) == 1:
            case_name = arguments[0]
            ert = self.ert()
            fs_manager = ert.getEnkfFsManager() 

            ert.getEnkfSimulationRunner().runWorkflows(HookRuntime.PRE_UPDATE)

            es_update = ESUpdate( ert )
            target_fs = fs_manager.getFileSystem(case_name)
            source_fs = fs_manager.getCurrentFileSystem( )
            model_config = ert.getModelConfig( )
            runpath_fmt = model_config.getRunpathFormat( )
            subst_list = ert.getDataKW( )
            mask = BoolVector( default_value = True, initial_size = ert.getEnsembleSize( ) )
            
            run_context = ErtRunContext.ensemble_smoother( source_fs , target_fs , mask, runpath_fmt, subst_list, 0 )
            success = es_update.smootherUpdate( run_context  )

            if not success:
                self.lastCommandFailed("Unable to perform update")

            ert.getEnkfSimulationRunner().runWorkflows(HookRuntime.POST_UPDATE)

        else:
            self.lastCommandFailed("Expected one argument: <target_fs> received: '%s'" % line)
