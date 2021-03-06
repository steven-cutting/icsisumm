import sys, os, re
import framework, berkeleyparser, concept_mapper, ordering, compression
from globals import *

def parse_options():
    ## setup options parser
    from optparse import OptionParser
    usage = 'usage: %prog [options]'
    parser = OptionParser(usage=usage)

    parser.add_option('-t', '--task', dest='task', type='str',
                      help='tasks: u08, u07, m07, m06, m05, <text file>')
    parser.add_option('-d', '--dataroot', dest='dataroot', type='str',
                      help='dataroot: directory to store partial state')
    parser.add_option('--reload', dest='reload', default=False, action='store_true',
                      help='reload document data from scratch')
    parser.add_option('--compress', dest='compress', default=False, action='store_true',
                      help='use sentence compression when generating summaries')
    parser.add_option('--output', dest='output', default='out', type='str',
                      help='output directory for summaries')
    (options, args) = parser.parse_args()

    if options.task == 'u08': task = TAC_2008_UPDATE_TASK
    elif options.task == 'u07': task = DUC_2007_UPDATE_TASK
    elif options.task == 'm07': task = DUC_2007_MAIN_TASK
    elif options.task == 'm06': task = DUC_2006_MAIN_TASK
    elif options.task == 'm05': task = DUC_2005_MAIN_TASK
    else:
        parser.error('unrecognized task [%s], use --help to get a list of valid tasks' %options.task)

    if options.dataroot:
        os.popen("mkdir -p " + options.dataroot)
        task.data_pickle = '%s/%s_data.pickle' %(options.dataroot, task.name)
        task.punkt_pickle = '%s/%s_punkt.pickle' %(options.dataroot, task.name)

    return options, task

if __name__ == '__main__':
    
    options, task = parse_options()

    ## create SummaryProblem instances
    if options.task == 'u08':
        framework.setup_TAC08(task)
    else:
        framework.setup_DUC_basic(task)

    # only run the parser if compression is required (this is not known by the pickle stuff)
    parser = None
    if options.compress:
        parser = berkeleyparser.CommandLineParser(BERKELEY_PARSER_CMD)
    framework.setup_DUC_sentences(task, parser, reload=options.reload)

    #for problem in task.problems:
    #    for sentence in problem.get_new_sentences():
    #        print sentence.parsed
    #sys.exit(0)

    ## create output directory
    try: os.popen('rm -rf %s' %options.output)
    except: pass
    os.mkdir(options.output)

    if options.compress:
        ## sentence compression
        for problem in task.problems:
            #if problem.id != 'D0716-A': continue
            # update stemming
            for sentence in problem.get_new_sentences():
                sentence.set_text(sentence.original)
            #    sentence.stemmed = sentence.no_stop
            problem.query.set_text(problem.query.original)
            #problem.query.stemmed = problem.query.no_stop

            #if problem.id != 'D0704': continue
            sys.stderr.write("%s %d\n" % (problem.id, sum([len(doc.sentences) for doc in problem.new_docs])))
            acronyms = framework.removeAcronymsFromProblem(problem)
            mapper = concept_mapper.HeuristicMapperExp(problem, "n2", None)
            mapper.map_concepts()
            mapper.choose_sents()
            concept_weight = mapper.concept_weight_sets[0]
            #print concept_weight.keys()
            #program = framework.build_program(problem, concept_weight, length=task.length_limit, sentences=mapper.relevant_sent_sets[0])
            program = framework.build_alternative_program(problem, concept_weight, length=task.length_limit, sentences=mapper.relevant_sent_sets[0], longuest_candidate_only=False, providedAcronyms=acronyms)
            # run the program and get the output
            program.debug = 0
            program.run()
            #selection = framework.get_program_result(program)
            selection = []
            for variable in program.output:
                if re.match(r'^s\d+$', variable) and program.output[variable] == 1:
                    selection.append(program.binary[variable])
            if len(selection) == 0:
                sys.stderr.write('ERROR: empty summary, check the output of the solver\n')
                sys.exit(1)
            #selection = ordering.by_date(selection)
            selection = ordering.by_dendrogram(selection, concept_weight, problem)
            summary = "\n".join(sentence.original for sentence in selection)
            summary = compression.addAcronymDefinitionsToSummary(summary, program.acronyms)
            #print summary
            output_file = open("%s/%s" % (options.output, problem.id), "w")
            output_file.write(summary)
            output_file.close()

            # allow memory cleanup
            problem.old_problems = []
            problem.old_docs = []
            problem.new_docs = []
    else:    
        ## no sentence compression
        for problem in task.problems:
            for sentence in problem.get_new_sentences():
                sentence.set_text(sentence.original)
            problem.query.set_text(problem.query.original)
            sys.stderr.write("%s %d\n" % (problem.id, sum([len(doc.sentences) for doc in problem.new_docs])))
            mapper = concept_mapper.HeuristicMapperExp(problem, "n2", None)
            #mapper = concept_mapper.CheatingMapper(problem, "n2", None)
            mapper.map_concepts()
            mapper.choose_sents()
            selection = mapper.format_output("ilp", task.length_limit)
            selection = ordering.by_date(selection)
            output_file = open("%s/%s" % (options.output, problem.id), "w")
            for sentence in selection:
                output_file.write(sentence.original + "\n")
            output_file.close()
    ## evaluate
    if options.task != 'u08':
        cmd = '%s %s %s' %(ROUGE_SCORER, task.manual_path, options.output)
        eval = os.popen(cmd).read()
        [rouge_1, rouge_2, rouge_su4] = re.findall(': (\d\.\d+)', eval)
        print eval
