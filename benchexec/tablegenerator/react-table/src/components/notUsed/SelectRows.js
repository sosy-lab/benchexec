import React from 'react';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faTimes } from '@fortawesome/free-solid-svg-icons'
import Collapsible from 'react-collapsible';
export default class SelectColumn extends React.Component {

    constructor(props) {
        super(props);
        this.state= {
            showOverlay: this.props.close,
            column: this.props.currColumns,
            activeFilter: [],
            min: '',
            max: '',
        };
        this.renderRunSets = this.renderRunSets.bind(this);
        this.renderPossibleFilter = this.renderPossibleFilter.bind(this);
        this.applyFilter = this.applyFilter.bind(this);
        this.handleChangeMin = this.handleChangeMin.bind(this);
        this.handleChangeMax = this.handleChangeMax.bind(this);
        this.renderActiveFilter = this.renderActiveFilter.bind(this);
    }

    renderRunSets() {
        return this.props.tools.map((tool, i) => {
            return <div key={`div-`+this.props.getRunSets(tool)}> 
                    <h4> {this.props.getRunSets(tool)} </h4> 
                        {this.renderPossibleFilter(tool, i)}
                </div>
        })
    }
    renderPossibleFilter(tool, i) {
        return tool.columns.map((column, index) => {
            return <Collapsible trigger={this.renderActiveFilter(i, column, index)} key={column.title}>
                {this.renderContent(i, column, index)}
                </Collapsible>
        })
    }
    renderContent(tool, column, index) {
        if (column.type.name !== "main_status" && column.type.name !== "text") {
            return  <div className="contentInner">
                        <label className="contentInner--input">
                            Min: <input className="borderValue" value={this.state.min} onChange={this.handleChangeMin} type="text"></input>Max: <input className="borderValue" type="text" onChange={this.handleChangeMax} value={this.state.max}></input>
                        </label>
                        <div className="contentInner--buttons">
                            <button className="btn btn-apply" onClick={(e) => this.applyFilter(e, tool, index)}>apply</button>
                        </div>
                    </div>
        } else {
            return <input placeholder="Search me"></input>
        }
    }
    applyFilter(ev, tool, column) {
        //prepare Filter and add to active Filter in state
        let filter = `${tool}-${column}-${this.state.min}-${this.state.max}`; 
        this.setState(prevState => ({
            activeFilter: [...prevState.activeFilter, filter],
            min: '',
            max: '',
        }));
    }
    handleChangeMin(event) {
        this.setState({min: event.target.value});
    }
    handleChangeMax(event) {
        this.setState({max: event.target.value});
    }

    renderActiveFilter(tool, column, index) {
        //wenn ein String aus dem array this.state.filterArray am Anfang mit tool-column übereinstimmt
        let hasFilter = this.state.activeFilter.find(filter => {
            return filter.startsWith({tool}+'-'+{index}+'-')
        })
        if (hasFilter !== undefined) {
            return <span>{column.title} HasFilter</span>
        } else {
            return <span>{column.title} Min and max</span>

        }
    }

    render() {
        return (
            <div className="overlay filterRows">
                <FontAwesomeIcon icon={faTimes} onClick={this.props.close} className="closing" />
                <h1>Filter your Rows</h1>
                <div className="filterRows__inner">
                    <div className="filterRows__possibleFilter">{this.renderRunSets()}</div>
                    <div className="filterRows__activeFilter"><h4>My activated filters</h4></div>
                </div>
                <div className="buttonBar">
                    <input type="text"></input><button className="btn">apply task filter</button>
                    <button className="btn btn-apply" onClick={(e) => this.props.filter(e, this.state.activeFilter)}>Apply Filter and close</button>
                    <button className="btn" onClick={this.props.reset}>Reset Filters and close</button>
                </div>
            </div>
        )
    }
}