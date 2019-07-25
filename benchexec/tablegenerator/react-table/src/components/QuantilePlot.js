import React from 'react';
import '../../node_modules/react-vis/dist/style.css';
import {XYPlot, LineMarkSeries, VerticalGridLines, HorizontalGridLines, XAxis, YAxis, DiscreteColorLegend, Hint} from 'react-vis';
export default class Overlay extends React.Component {
    constructor(props) {
        super(props);
        
        const visibleColumn = this.props.preSelection.isVisible ? 
                    this.props.preSelection : this.props.tools.map(tool => tool.columns).flat().find(col => col.isVisible);
        
        this.state = {
            selection: visibleColumn.title,
            quantile: true,
            linear: false,
            correct: true,
            isValue: true, //one Value more RunSets = true; oneRunSet more Values = false
            isInvisible: [], 
        }

        this.possibleValues = [];
        this.initialLines = [];
        this.strokeStyle = "";
    };
    renderLegend = () => {
        return (this.state.isValue) 
            ? this.props.tools.filter(t => t.isVisible).map(tool => { 
                return this.props.getRunSets(tool);
            }) 
            : this.props.tools[this.state.selection.split('-')[1]].columns.map(c => c.isVisible ? c.title : null).filter(Boolean);
    }

    renderAll = () => {
        let task = this.state.selection;
        if (this.state.isValue) {
            //var 1: compare different RunSets on one value
            this.props.tools.forEach((tool, i) => {
                this[task+i]= [];
                this.renderData(this.props.table, task, i, this[task+i])
            })
        } 
        else {
            //var 2: compare different values of one RunSet
            let index = this.state.selection.split('-')[1]
            this.props.tools[index].columns.forEach((column, i) => {
                if (!(column.type.name === "main_status" || column.type.name === "text") && column.isVisible) {
                    this[column.title] = [];
                    return this.renderData(this.props.table, column.title, index, this[column.title])
                }
            })
        }
    }
    renderData = (runSets, column, tool, data) => {
        let arrayY = [];
        const index = this.props.tools[tool].columns.findIndex(value => value.title === column);
        if(!this.state.isValue || index >= 0) {
            if(this.state.correct) {
                runSets.forEach(runSet => {
                    if(runSet.results[tool].category === "correct") {
                        arrayY.push([this.props.preparePlotValues(runSet.results[tool].values[index], tool, +index), runSet.short_filename]);
                    } 
                });
            } else {
                runSets.forEach(runSet => {
                    arrayY.push([this.props.preparePlotValues(runSet.results[tool].values[index], tool, +index), runSet.short_filename]);
                });
            }
            if(this.state.quantile) {
                const currentValue = this.possibleValues.find(value => value.title === column);
                if(this.state.isValue && (currentValue.type.name==="text" || currentValue.type.name==="main_status")) {
                    arrayY.sort((a,b) => (a[0] > b[0]) ? 1 : ((b[0] > a[0]) ? -1 : 0)); ;
                } else {
                    arrayY.sort((a, b) => (a[0] - b[0]));
                }
            }
        }
        
        arrayY.forEach((el, i) => {
            const value = el[0];
            const isLogAndInvalid = !this.state.linear && value <= 0;

            if(value !== null && !isLogAndInvalid) {
                data.push({
                    x: i,
                    y: value,
                    info: el[1]
                });
            }
        });
    }

    renderColumns = () => {
        this.props.tools.forEach(tool => {
            tool.columns.forEach(column => {
                if (column.isVisible && this.possibleValues.findIndex(value => value.title === column.title) < 0) {
                    this.possibleValues.push(column)
                } 
            })
        })
        // kann man den oberen Teil rausziehen? Muss nur initial gemacht werden
        this.renderAll();
        return this.possibleValues.map(value => {
            return <option key={value.title} value={value.title} name={value.title}>{value.title}</option>
        })
    }

    renderLines = () => {
        this.lineArray = this.initialLines;
        if (this.state.isValue) {
            return this.props.tools.map((tool, i) => {
                let task = this.state.selection;
                let data = this[task+i] 
                return (data.length > 0 && tool.isVisible) ? 
                <LineMarkSeries data={data} key={tool.benchmarkname+tool.date} opacity={this.handleLineState(this.props.getRunSets(tool))} onValueMouseOver={(datapoint, event) => this.setState({value: datapoint})} onValueMouseOut={(datapoint, event) => this.setState({value: null})}/> : 
                null
            }).filter(el => !!el);
        } else {
            let index = this.state.selection.split('-')[1]
            return this.props.tools[index].columns.map((column, i) => {
                let data = this[column.title];
                this.lineArray.push(column.title)
                return <LineMarkSeries data={data} key={column.title} opacity={this.handleLineState(column.title)} onValueMouseOver={(datapoint, event) => this.setState({value: datapoint})} onValueMouseOut={(datapoint, event) => this.setState({value: null})}/>
            })
        }
    }

    handleLineState = (line) => {
        return this.state.isInvisible.indexOf(line) < 0 ? 1 : 0;
    }

    handleColumn = (ev) => {
        // let isValue;

        // if (ev.target.value.length < 4) {
        //     // this.setState({isValue: true});
        //     isValue = true;
        // } else {
        //     // this.setState({isValue: false});
        //     isValue = false
        // }
        // const isValue = ev.target.value.length < 4;
        //TODO: isValue is true, wenn ev.target.value in einem Tool als column.title vorkommt
        let isValue = this.props.tools.map(tool => {
            return (tool.columns.findIndex(value => value.title === ev.target.value) >= 0)}).findIndex(value => value === true) >= 0;
        this.setState({selection: ev.target.value, isValue: isValue });  
    }
    toggleQuantile = () => {
        this.setState(prevState => ({ 
            quantile: !prevState.quantile,
        }));
    }
    toggleCorrect = () => {
        this.setState(prevState => ({ 
            correct: !prevState.correct,
        }));
    }
    toggleLinear = () => {
        this.setState(prevState => ({ 
            linear: !prevState.linear,
        }));
    }
    toggleShow = ({ target }) => {
        const value = target.checked;
        const name = target.name;
        
        this.setState({
            [name]: value
        });
    }
    handlyType = () => {
        const { selection } = this.state;
        if (this.state.isValue) {
            const index = this.possibleValues.findIndex(value => value.title === selection);
            if((this.possibleValues[index].type && this.possibleValues[index].type.name==="text") || (this.possibleValues[index].type && this.possibleValues[index].type.name==="main_status")) {
                return 'ordinal'
            } else return this.state.linear ? 'linear': 'log'
        } else {
            return this.state.linear ? 'linear': 'log'
        }
    }
    
    
    render() {
        return (
            <div className="quantilePlot">
                <select name="Select Column" value={this.state.selection} onChange={this.handleColumn}>
                    <optgroup label="RunSets">
                        {this.props.tools.map((runset, i) => {
                            return runset.isVisible ? <option key={"runset-"+i} value={"runset-"+i} name={"runset-"+i}>{this.props.getRunSets(runset, i)}</option> : null;
                        })}
                    </optgroup>
                    <optgroup lable="columns">
                        {this.renderColumns()}
                    </optgroup>
                </select>
                <XYPlot height={window.innerHeight - 200} width={window.innerWidth - 100} margin={{left: 90}} yType={this.handlyType()}>
                    <VerticalGridLines />
                    <HorizontalGridLines />
                    <XAxis tickFormat = {(value) => value}/>
                    <YAxis tickFormat = {(value) => value}/>
                    {this.renderLines()}
                    {this.state.value ? <Hint value={this.state.value} /> : null}
                    <DiscreteColorLegend 
                        items={this.renderLegend()} 
                        onItemClick={(Object, item) => {
                            let line = '';
                            this.state.isValue ? line = Object.toString() : line = Object.toString();
                            if (this.state.isInvisible.indexOf(line) < 0) {
                                this.setState({
                                    isInvisible: this.state.isInvisible.concat([line])
                                })
                            } else {
                                return this.setState({isInvisible: this.state.isInvisible.filter(l => {
                                    return l !== line
                                })});
                            }
                        }}
                    />
                </XYPlot>
                    <button className="btn" onClick={this.toggleQuantile}>{this.state.quantile ? 'Switch to Direct Plot' : 'Switch to Quantile Plot'}</button>
                    <button className="btn" onClick={this.toggleLinear}>{this.state.linear ? 'Switch to Logarithmic Scale' : 'Switch to Linear Scale'}</button>
                    <button className="btn" onClick={this.toggleCorrect}>{this.state.correct ? 'Switch to All Results' : 'Switch to Correct Results Only'}</button>
            </div>
        )
    }
}