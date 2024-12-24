const levels = {
    DEBUG: 'DEBUG',
    INFO: 'INFO',
    WARN: 'WARN',
    ERROR: 'ERROR'
};

// Assume we are in development mode if `window` exists and no explicit flag is set
//const isDebugMode = window.location.hostname === 'localhost' || window.DEBUG_MODE === true;
const isDebugMode = true;

function log(message, level = levels.INFO) {
    if (!isDebugMode && level === levels.DEBUG) return; // Skip debug logs in non-debug mode

    const timestamp = new Date().toISOString();
    switch (level) {
        case levels.DEBUG:
            console.debug(`[DEBUG] [${timestamp}] ${message}`);
            break;
        case levels.INFO:
            console.info(`[INFO] [${timestamp}] ${message}`);
            break;
        case levels.WARN:
            console.warn(`[WARN] [${timestamp}] ${message}`);
            break;
        case levels.ERROR:
            console.error(`[ERROR] [${timestamp}] ${message}`);
            break;
        default:
            console.log(`[LOG] [${timestamp}] ${message}`);
    }
}

const logger = {
    debug: (message) => log(message, levels.DEBUG),
    info: (message) => log(message, levels.INFO),
    warn: (message) => log(message, levels.WARN),
    error: (message) => log(message, levels.ERROR)
};

export default logger;