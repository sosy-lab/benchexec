import React from 'react';
import ReactTable from 'react-table'
import 'react-table/react-table.css'
import withFixedColumns from 'react-table-hoc-fixed-columns';
import 'react-table-hoc-fixed-columns/lib/styles.css'
import "react-table/react-table.css";
import Utils from '../utils/utils'

const ReactTableFixedColumns = withFixedColumns(ReactTable);
export default class Table extends React.Component {

    constructor(props) {
        super(props);
        this.data = this.props.data;
        this.state = {
            fixed: true,
            showLinkOverlay: false,
            link: '',
        };

        this.infos = ['displayName', 'tool', 'limit', 'host', 'os', 'system', 'date', 'runset', 'branch', 'options', 'property'];
        this.typingTimer = -1;
        this.width = (window.innerWidth*0.3);
        this.height = window.innerHeight-50;
    };

    handleInputChange = (event) => {
        const target = event.target;
        const value = target.checked;
        const name = target.name;
    
        this.setState({
          [name]: value
        });
      }


    renderColumns = () => {
        return this.props.tools.map((tool, j) => {
            return tool.columns.map((column, i) => {
                if(column.type.name === "main_status" || column.type.name === "status") {
                    return {
                        id: `${j}_${column.display_title}_${i}`,
                        Header: () => (
                            <span title="Click here to sort. Hold shift to multi-sort" className="btn">{column.display_title}{column.unit ? ` (${column.unit})` : ''}</span>
                        ),
                        show: column.isVisible,
                        accessor: props => (
                            this.props.prepareTableValues(props.results[j].values[i], j, i, props.results[j].href, props.results[j])
                        ),
                        sortMethod: (a, b, desc) => {
                            //default hast to be overwritten because of <span>
                            a = a ? a.props.children : null
                            b = b ? b.props.children : null
                            a = a === null || a === undefined ? -Infinity : a
                            b = b === null || b === undefined ? -Infinity : b
                            a = typeof a === 'string' ? a.toLowerCase() : a
                            b = typeof b === 'string' ? b.toLowerCase() : b
                            if (a > b) {
                              return 1
                            }
                            if (a < b) {
                              return -1
                            }
                            return 0
                          },
                        filterMethod: (filter, row) => {
                            switch(filter.value) {
                                //case category has to be differentiated to the name of the status => space in String
                                case "all ": {
                                    return true;
                                }
                                case "correct ": {
                                    if(row._original.results[j].category === 'correct') {
                                        return row[filter.id]
                                    }
                                    break;
                                } 
                                case "wrong ": {
                                    if(row._original.results[j].category === 'wrong') {
                                        return row[filter.id]
                                    }
                                    break;
                                }
                                case "ERROR ": {        
                                    if(row._original.results[j].category === 'error') {
                                        return row[filter.id]
                                    }
                                    break;
                                }
                                default: {
                                    if(row[filter.id] && filter.value === row[filter.id].props.children) {
                                        return row[filter.id]
                                    }
                                }
                            }
                        },
                        Filter: ({ filter, onChange }) => {
                            return  <select
                                        onChange={event => onChange(event.target.value)}
                                        style={{ width: "100%" }}
                                        value = {filter ? filter.value : "all"}
                                    >
                                        <optgroup label="Category">
                                            <option value = "all ">Show all</option>
                                            <option value = "correct ">correct</option>
                                            <option value = "wrong ">wrong</option>
                                            <option value = "ERROR ">ERROR</option> 
                                        </optgroup>
                                        <optgroup>
                                            {this.collectStati(j, i)}
                                        </optgroup>
                                    </select> 
                        }
                    }
                } else { 
                    return {
                        id: `${j}_${column.display_title}_${i}`,
                        Header: () => (
                            <div title="Click here to sort. Hold shift to multi-sort"> {column.display_title}{column.unit ? ` (${column.unit})` : ''} </div>
                        ),
                        show: column.isVisible,
                        accessor: props => (
                            this.props.prepareTableValues(props.results[j].values[i], j, i)
                            // console.log(this.props.prepareTableValues(props.results[j].values[i], j, i))
                        ),
                        Cell: row => {
                            return <div dangerouslySetInnerHTML={{ __html: row.value.formatted }} />
                        },
                        filterMethod: Utils.filterByRegex,
                        Filter: ({ filter, onChange }) => {
                            let value;
                            let type = column.type._type._type ? column.type._type._type : column.type._type;
                            let placeholder = (type === 2 || type === 3) ? 'Min:Max' : 'text'
                            return (
                                <input
                                    placeholder = {placeholder}
                                    defaultValue = {value ? value : (filter ? filter.value : filter)}
                                    onChange = {event => {
                                        value = event.target.value
                                        clearTimeout(this.typingTimer)
                                        this.typingTimer = setTimeout(() => {
                                            onChange(value)
                                        }, 500)}
                                    }
                               />  
                         )},
                        sortMethod: Utils.sortMethod
                    }
                }
            });
        });
    }

    collectStati = (tool, column) => {
        let statiArray = this.data.map(row => {
            return row.results[tool].values[column].formatted
        });
        return [...new Set(statiArray)].map(status => {
            return status ? <option value = {status} key = {status}>{status}</option> : null
        })
    }
    renderToolInfo = (i) => {
        let header = this.props.tableHeader;
        
        return this.infos.map(row => {
            return (header[row]) ? <p key={row} className="header__tool-row">{header[row].content[i][0]} </p> : null;
        })
    }
    
    render() {
        this.data = this.props.data;
        const toolColumns = this.renderColumns(); // TODO rename method
        let columns = 
        [
            {
                Header: () => (
                    <div className="fixed">
                        <form>
                            <label title="Fix the first column">
                                Fixed task:
                            </label>
                            <input name="fixed" type="checkbox" checked={this.state.fixed} onChange={this.handleInputChange} />
                        </form>
                    </div>
                ),
                fixed: this.state.fixed ? 'left' : '',
                columns: [
                    {
                        width: this.width,
                        id: 'short_filename',
                        Header: () => (
                            <div
                                onClick={this.props.selectColumn}
                                className={"selectColumns"}
                            >
                                <span>Click here to select columns</span>
                            </div>
                        ),
                        fixed: this.state.fixed ? 'left' : '',
                        accessor: props => (
                                props.has_sourcefile 
                                    ?   <a key = {props.href} className={props.href ? 'row__name--cellLink' : 'row__name'} href={props.href} title="Click here to show source code" onClick={ev => this.props.toggleLinkOverlay(ev, props.href)}> 
                                            {props.short_filename} {props.id.filter((id, i) => id !== null && i !== 0 && this.props.properties[i]).map(id => <span key = {id} className="row_id">{id}</span>)}  
                                        </a> 
                                    : <span key = {props.href} title="This task has no associated file">{props.short_filename} {props.id.filter((id, i) => id !== null && i !== 0 && this.props.properties[i]).map(id => <span className="row_id">{id}</span>)}</span>
                        ),
                        filterMethod: (filter, row, column) => {
                            const id = filter.pivotId || filter.id
                            return row[id].props.children !== undefined ? String(row[id].props.children).includes(filter.value) : false;
                        },

                    }
                ]
            },
            ...toolColumns.map((toolColumn, i) => {
                return {   
                    id: 'results',
                    Header: () => (
                        <span className="header__tool-infos">
                            {this.props.getRunSets(this.props.tools[i])}
                        </span>
                    ),
                    columns: toolColumn,
                };
            })
        ]
        
        return (
            <div className ="mainTable">
                <ReactTableFixedColumns
                    data={this.data}
                    filterable = {true}
                    filtered = {this.props.filtered}
                    // style = {{ borderRight: '1px solid rgba(142, 142, 142, 0.7)', backgroundColor: '#dadada',}}
                    columns= {columns}
                    defaultPageSize = {250}
                    pageSizeOptions={[50, 100, 250, 500, 1000, 2500]}
                    className = "-highlight"
                    minRows = {0}
                    onFilteredChange={filtered => {
                        this.props.filterPlotData(filtered);
                    }}
                    style={{ maxHeight: this.height }}
                >
                    {(state, makeTable, instance) => {
                        this.props.setFilter(state.sortedData);
                        return (
                            makeTable()
                        )
                    }}
                </ReactTableFixedColumns>

            </div>
        )
    }
}