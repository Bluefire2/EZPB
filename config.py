config_types = {
    'generations': {
        'max_discard': int,
        'min_cycles': int
    },
    'thresholds': {
        'max_gen': int,
        'min_loglik_rel_diff': float,
        'max_loglik_effsize': int,
        'min_maxdiff': float
    },
    'default': {
        'tree_sample_freq': int,
        'check_freq': int
    },
    'output': {
        'tracecomp': str,
        'loglik_line': int,
        'bpcomp': str,
        'max_diff_line': int,
        'directory': str
    },
    'input': {
        'filetypes': str
    }
}