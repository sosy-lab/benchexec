import React from 'react';
import ReactTable from 'react-table'
import 'react-table/react-table.css'
import withFixedColumns from 'react-table-hoc-fixed-columns';
import 'react-table-hoc-fixed-columns/lib/styles.css'

const ReactTableFixedColumns = withFixedColumns(ReactTable);

export default class Summary extends React.Component {

    constructor(props) {
        super(props);
        this.state= {
            showTotal: true,
            showLocal: true,
            showCorrect: true,
            showIncorrect: true,
            fixed: true,
        }
        this.infos = ['displayName', 'tool', 'limit', 'host', 'os', 'system', 'date', 'runset', 'branch', 'options', 'property'];

    };
    handleInputChange = (event) => {
        const target = event.target;
        const value = target.checked;
        const name = target.name;
    
        this.setState({
          [name]: value
        });
      }

    renderResultTable = () => {
        return this.props.tools.map((tool, j) => {
            
            return tool.columns.map((column, i) => {
                
                return {
                    id: column.title+j,
                    Header: () => (
                        <div className="columns" title="Show Quantile Plot of this column" onClick={(e) => this.props.changeTab(e, i, 2)}>{column.title + (column.source_unit ? " (" + column.source_unit + ")" : '')}</div>
                        ),
                        show: column.isVisible,
                        accessor: props => (
                        props.content[j][i] ? <div className="summary_span">{this.props.prepareTableValues(props.content[j][i].sum, j, i)}</div> : <div className="summary_span">-</div>
                    ),
                }
            });
        });
    }

    renderToolInfo = (i) => {
        let header = this.props.tableHeader;
        
        return this.infos.map(row => {
            return (header[row]) ? <p key={header[row].id} className="header__tool-row">{header[row].content[i][0]} </p> : null;
        })
    }

    render() {
        const toolColumns = this.renderResultTable();
        const column = 
            [
                {
                    Header: () => (
                        <div className="toolsHeader">
                            <form>
                                <label>
                                    Fixed:
                                </label>
                                <input name="fixed" type="checkbox" checked={this.state.fixed} onChange={this.handleInputChange} />
                            </form>
                                {this.infos.map(row => {
                                    return this.props.tableHeader[row] ? <p key={row}> {row} </p> : null
                                })}
                        </div>
                    ),
                    fixed: this.state.fixed ? 'left' : '',
                    columns: [
                        {
                            minWidth: 250,
                            id: 'summary',
                            Header: () => (
                                <div
                                    onClick={this.props.selectColumn}
                                >
                                    <span>Click here to select columns</span>
                                </div>
                            ),
                            accessor: props => (
                                <div dangerouslySetInnerHTML={{ __html: props.title }} title={props.description}/>
                            )
                        }
                    ]
                },
                ...toolColumns.map((toolColumn, i) => {
                    return {   
                        id: 'results',
                        Header: () => (
                            <div className="header__tool-infos">
                                {this.renderToolInfo(i)}
                            </div>  
                        ),
                        columns: toolColumn
                    };
                })
            ]

        return (
             <div className = "summary">
                <ReactTableFixedColumns
                    data={this.props.stats}
                    columns= {column}
                    showPagination={false}
                    className = "-highlight"
                    minRows = {0}
                    sortable = {false}
                />
            </div>
        )
    }
}