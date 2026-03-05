/**
 * Script to remove console.log statements from source files
 * Run with: node scripts/remove_console_logs.js
 */

const fs = require('fs');
const path = require('path');

// Files to process
const filesToProcess = [
    'web/src/stores/graphStore.js',
    'web/src/stores/agent.js',
    'web/src/components/KnowledgeGraphViewer.vue',
    'web/src/components/KnowledgeGraphSection.vue',
    'web/src/components/FileTable.vue',
    'web/src/components/DebugComponent.vue',
    'web/src/components/RefsComponent.vue',
    'web/src/views/SettingView.vue',
    'web/src/views/AgentView.vue',
    'web/src/utils/chatExporter.js',
    'web/src/apis/base.js',
];

// Patterns to remove (entire lines containing these)
const patternsToRemove = [
    /^\s*console\.log\([^)]*\);?\s*$/gm,
    /^\s*console\.log\(([\s\S]*?)\);\s*$/gm,
];

// Pattern for multi-line console.log
const multiLineConsoleLog = /console\.log\([^)]*\n[^)]*\);?/g;

function removeConsoleLogs(content) {
    let result = content;

    // Remove single-line console.log with their full line
    result = result.replace(/^[ \t]*console\.log\([^;]*\);[ \t]*\r?\n/gm, '');

    // Remove console.log inside template or as attribute value like @click="console.log(msg)"
    result = result.replace(/@click="console\.log\([^"]*\)"/g, '@click=""');

    // Remove multi-line console.log blocks
    result = result.replace(/[ \t]*console\.log\([^)]*\n[^)]*\);?\r?\n/g, '');

    // Remove if blocks that only contain console.log
    result = result.replace(/if \([^)]+\) \{\s*\n\s*console\.log\([^)]*\);\s*\n\s*\}/g, '');

    return result;
}

function processFile(filePath) {
    const fullPath = path.join(__dirname, '..', filePath);

    if (!fs.existsSync(fullPath)) {
        console.log(`Skipping (not found): ${filePath}`);
        return 0;
    }

    const content = fs.readFileSync(fullPath, 'utf8');
    const original = content;
    const processed = removeConsoleLogs(content);

    if (processed !== original) {
        fs.writeFileSync(fullPath, processed, 'utf8');
        const removedCount = (original.match(/console\.log/g) || []).length -
            (processed.match(/console\.log/g) || []).length;
        console.log(`Processed: ${filePath} (removed ~${removedCount} console.log calls)`);
        return removedCount;
    } else {
        console.log(`No changes: ${filePath}`);
        return 0;
    }
}

console.log('Removing console.log statements from source files...\n');

let totalRemoved = 0;
filesToProcess.forEach(file => {
    totalRemoved += processFile(file);
});

console.log(`\nTotal console.log statements removed: ~${totalRemoved}`);
