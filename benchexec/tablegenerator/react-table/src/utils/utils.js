export default {

    prepareTableData(data) {
        return {
            tableHeader: data.head,
            tools: data.tools.map(tool => ({
                ...tool, 
                isVisible: true, 
                columns: tool.columns.map(c => ({ ...c, isVisible: true }))
            })),
            columns: data.tools.map(t => t.columns.map(c => c.title)),
            table: data.rows,
            stats: data.stats,
            properties: data.props,
        };
    },

    filterByRegex(filter, row, cell) {
        const pattern = /((-?\d*\.?\d*):(-?\d*\.?\d*))|(-?\d*\.?\d*)/

        const regex = filter.value.match(pattern);
        if (regex[2] === undefined) {
            return String(row[filter.id].formatted).startsWith(filter.value);
        } else if(!(regex[3])) {
            if (+row[filter.id].original >= Number(regex[2])) {
                return row[filter.id]
            }
        } else if(!(regex[2])) {
            if (+row[filter.id].original <= Number(regex[3])) {
                return row[filter.id];
            }
        } else if (row[filter.id].original >= Number(regex[2]) && row[filter.id].original <= Number(regex[3])){
            return row[filter.id];
        }
        return false;
    },

    sortMethod(a, b) {
        a = +a.original
        b = +b.original
        a = a === null || a === undefined ? -Infinity : a
        b = b === null || b === undefined ? -Infinity : b
        // a = typeof a === 'string' ? a.toLowerCase() : a
        // b = typeof b === 'string' ? b.toLowerCase() : b
        if (a > b) {
            return 1
        }
        if (a < b) {
            return -1
        }
        return 0
    },
}