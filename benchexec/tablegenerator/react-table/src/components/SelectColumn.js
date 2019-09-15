import React from 'react';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faTimes } from '@fortawesome/free-solid-svg-icons'
export default class SelectColumn extends React.Component {

    constructor(props) {
        super(props);
        this.state= {
            showOverlay: this.props.close,
            column: this.props.currColumns,
            deselect: true,
            list: this.props.tools,
        }
        this.tableHeader = this.props.tableHeader;
        this.activeColumns = this.possibleColumns;
        this.selectable = [];
    };
   
// -------------------------Closing-------------------------
    close = () => {
        this.props.select()
        this.setState(prevState => ({ 
            showOverlay: !prevState.showOverlay,
        }));
    };
    escFunction = (event) => {
        if(event.keyCode === 27) {
          this.props.close();
        }
    }
    componentDidMount = () => {
    document.addEventListener("keydown", this.escFunction, false);
    }
    componentWillUnmount = () => {
    document.removeEventListener("keydown", this.escFunction, false);
    }
    
// -------------------------Rendering-------------------------
    renderRunSets = () => {
        return this.props.tools.map((tool, i) => {
            let isVisible = this.props.tools[i].columns.findIndex(value => value.isVisible === true) > -1;
            let toolName = this.props.getRunSets(tool);
            return  <tr id={toolName} key={'tr'+toolName}><td id={toolName} key={'key'+toolName} className={isVisible ? 'checked' : ''}>
                <label>
                    {toolName}<input name={toolName} type="checkbox" checked={isVisible} onChange={(e) => this.deselectTool(i, e)}></input>
                </label>
                </td>{this.renderColumns(i)}</tr>
        });
    };
    renderColumns = (index) => {
        return this.props.tools[index].columns.map(column => {
            return  <td id={'td'+index+column.display_title} key={'key'+index+column.display_title} className={column.isVisible ? 'checked' : ''}>
                    <label>
                        {column.display_title}<input id={index+'--'+column.display_title} name={index+'--'+column.display_title} type="checkbox" checked={column.isVisible} onChange={this.handleSelecion}></input>
                    </label>
                    </td>
        });
    }

    renderSelectColumns = () => {
        this.props.tools.forEach(tool => {
            tool.columns.forEach(column => {
                if (this.selectable.findIndex(value => value.display_title === column.display_title) < 0) {
                    this.selectable.push(column)
                } 
            })
        })
        return this.selectable.map((column, i) => {
            //column.isVisible === all columns true
            //in all tools => in Tool: column with column.title? => isVisible?
            return <th id={'td-all-'+column.display_title} key={'key'+column.display_title} className={column.isVisible ? 'checked' : ''}>
                <label>
                    {column.display_title}<input name={column.display_title} type="checkbox" checked={column.isVisible} onChange={this.handleSelectColumns}></input>
                </label>
                </th>
        })
    }

// -------------------------Handling-------------------------
    handleSelecion = (event) => {
        const target = event.target;
        const value = target.type === 'checkbox' ? target.checked : target.value;
        let name = target.name;
        let split = name.split('--')
        let tool = split[0];
        let column = split[1];

        let index = this.props.tools[tool].columns.findIndex(el => el.display_title === column)
        let list = this.props.tools
        list[tool].columns[index].isVisible = value;
        this.setState({ list: list })
        
    }

    handleSelectColumns = (event) => {
        let target = event.target;
        let value = target.type === 'checkbox' ? target.checked : target.value;
        let name = target.name;

        let list = this.state.list;
        list.forEach(tool => {
            let index = tool.columns.findIndex(el => el.display_title === name)
            if(tool.columns[index]) {
                tool.columns[index].isVisible = value
                this.setState({ list: list });
            }
        })
        //if all columns are deselected: isVisibile: false else isVisible: true
    }
    deselectTool = (i, event) => {
        const target=event.target
        const value = target.type === 'checkbox' ? target.checked : target.value;
        let list = this.state.list;
        list[i].columns.map(column => {
            return column.isVisible = value;
        })
        this.setState({ list: list });
        list[i].isVisible = value;
    }

    deselectAll = () => {
        if(this.state.deselect) {
            this.props.tools.map(tool => {
                return tool.columns.map(column => {
                    return column.isVisible = false;
                })
            })
        } else {
            this.props.tools.map(tool => {
                return tool.columns.map(column => {
                    return column.isVisible = true;
                })
            })
        }
        this.setState(prevState => ({ 
            deselect: !prevState.deselect,
        }));
    }
    checkTools = () => {
        this.props.tools.forEach(tool => {
            tool.columns.findIndex(column => column.isVisible) < 0 ? tool.isVisible = false : tool.isVisible = true;
        })
    }

    render() {
        this.checkTools();
        return (
            <div className="overlay">
                <FontAwesomeIcon icon={faTimes} onClick={this.props.close} className="closing" />
                <h1>Select the columns to display</h1>
                <table className="selectRows">
                    <tbody>
                        <tr className="selectColumn_all"><th></th>{this.renderSelectColumns()}</tr>
                        {this.renderRunSets()}
                    </tbody>
                </table>
                <div className="overlay__buttons">
                    <button className="btn" onClick={this.deselectAll}>{this.state.deselect ? 'Deselect all' : 'Select all'}</button>
                    <button className="btn btn-apply" onClick={this.props.close}>Apply and close</button>
                    <input/>
                </div>
            </div>
        )
    }
}