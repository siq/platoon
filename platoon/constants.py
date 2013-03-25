COMPLETED = 'completed'
FAILED = 'failed'
RETRY = 'retry'

PARTIAL = 206

PROCESS_TASK_ACTIONS = ('initiate-process',
    'report-abortion', 'report-completion', 'report-failure', 'report-progress',
    'report-timeout-to-executor', 'report-timeout-to-queue')
