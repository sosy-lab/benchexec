import React from 'react';
import '../../node_modules/react-vis/dist/style.css';
import {XYPlot, MarkSeries, VerticalGridLines, HorizontalGridLines, XAxis, YAxis, Hint, DecorativeAxis} from 'react-vis';
export default class ScatterPlot extends React.Component {
    constructor(props) {
        super(props);

        this.columns = this.props.column;
        this.state = {
            dataX: "0-1",
            dataY: "0-1",
            correct: true,
            linear: false,
            toolX: 0,
            toolY: 0,
            line: 10,
            columnX: 1,
            columnY: 1,
            nameX: this.props.getRunSets(this.props.tools[0]) + " " + this.props.columns[0][1],
            nameY: this.props.getRunSets(this.props.tools[0]) + " " + this.props.columns[0][1],
            value: false,
            width: window.innerWidth,
            height: window.innerHeight,
        }
        this.lineValues = [2, 3, 4, 5, 6, 7, 8, 9, 10, 100, 1000, 10000, 100000, 1000000, 10000000, 100000000]
        this.maxX = '';
        this.minX = '';
        this.lineCount = true;
    };

    componentDidMount() {
        window.addEventListener("resize", this.updateDimensions); // TODO add in quantile + maybe use debounce
    }

    componentWillUnmount() {
        window.removeEventListener("resize", this.updateDimensions);
    }

    updateDimensions = () => {
        this.setState({
            width: window.innerWidth,
            height: window.innerHeight,
        });
    }

    renderColumns = () => {
        return this.props.tools.map((runset, i) => {
            return <optgroup key={"runset"+i} label={this.props.getRunSets(runset, i)}>
                    {runset.columns.map((column, j) => {
                        return column.isVisible ? <option key={i+column.display_title} value={i+"-"+j} name={column.display_title}>{column.display_title}</option> : null
                    })}
                </optgroup>
        })
    }

    handlType = (tool, column) =>  {
        if(this.props.tools[tool].columns[column].type.name==="text" || this.props.tools[tool].columns[column].type.name==="main_status") {
            return 'ordinal'
        } else {
            return this.state.linear ? 'linear': 'log'
        }
    }

    renderData = () =>  {
        let array = [];
        this.arrayX = [];
        this.arrayY = [];

        if (this.state.correct) {
            this.props.table.forEach(row => {
                if(row.results[this.state.toolX].category==="correct" && row.results[this.state.toolY].category==="correct" && row.results[this.state.toolX].values[this.state.columnX] && row.results[this.state.toolY].values[this.state.columnY]) {
                    const x = row.results[this.state.toolX].values[this.state.columnX].original;
                    const y = row.results[this.state.toolY].values[this.state.columnY].original;
                    const isLogAndInvalid = !this.state.linear && (x <= 0 || y <= 0);
                    if(x !== null && y !== null && !isLogAndInvalid) {
                        array.push(
                            {
                                x: x,
                                y: y,
                                info: row.short_filename,
                            }
                        )
                    }
                }
            })
        } else {
            this.props.table.forEach(row => {
                if(row.results[this.state.toolX].values[this.state.columnX] && row.results[this.state.toolY].values[this.state.columnY]) {
                    const x = row.results[this.state.toolX].values[this.state.columnX].original;
                    const y = row.results[this.state.toolY].values[this.state.columnY].original;
                    const isLogAndInvalid = !this.state.linear && (x <= 0 || y <= 0);
                    if(x !== null && y !== null && !isLogAndInvalid) array.push(
                        {
                            x: x,
                            y: y,
                            info: row.short_filename,
                        }
                    ) 
                }
            })
        }
        this.maxX = this.findMaxValues(array)[0];
        this.maxY = this.findMaxValues(array)[1];
        this.minX = this.findMinValues(array)[0];
        this.minY = this.findMinValues(array)[1];
        (array.length === 0) ? this.lineCount = false : this.lineCount = true;
        this.dataArray = array;
    }
    findMaxValues = (array) => {
        const maxX = Math.max(...array.map(el => el.x)) < 3 ? 3 : Math.max(...array.map(el => el.x))
        const maxY = Math.max(...array.map(el => el.y)) < 3 ? 3 : Math.max(...array.map(el => el.y))
        return [maxX, maxY];
    }
    findMinValues = (array) => {
        const minX = Math.min(...array.map(el => el.x)) > 2 ? 1 : Math.min(...array.map(el => el.x))
        const minY = Math.min(...array.map(el => el.y)) > 2 ? 1 : Math.min(...array.map(el => el.y))
        return [minX, minY];
    }


    toggleCorrectResults = () => {
        this.setState(prevState => ({ 
            correct: !prevState.correct,
        }));
    }
    toggleLinear = () => {
        this.setState(prevState => ({
            linear: !prevState.linear,
        }))
    }

    handleX = (ev) => {
        this.array = [];
        let splitted = ev.target.value.split("-", 2)
        this.setState({ 
            dataX: ev.target.value, 
            toolX: splitted[0],
            columnX: splitted[1],  
            nameX: this.props.getRunSets(this.props.tools[splitted[0]]) + " " + this.props.columns[splitted[0]][splitted[1]],
        })
    }
    handleY = (ev) => {
        this.array = [];
        let splitted = ev.target.value.split("-", 2)
        this.setState({
            dataY: ev.target.value,
            toolY: splitted[0],
            columnY: splitted[1],  
            nameY: this.props.getRunSets(this.props.tools[splitted[0]])  + " " + this.props.columns[splitted[0]][splitted[1]],
        })
    }
    handleLine = ({target}) => {
        this.setState({
            line: target.value
        })
    }

    render() {
        this.renderData();
        return (
            <div className="scetterPlot">
                <div className="scetterPlot__select">
                    <span> X: </span><select name="Value XAxis" value={this.state.dataX} onChange={this.handleX}>
                        {this.renderColumns()}
                    </select>
                    <span> Y: </span><select name="Value YAxis" value={this.state.dataY} onChange={this.handleY}>
                        {this.renderColumns()}
                    </select>
                    <span>
                        Line: 
                    </span>
                    <select name="Line" value={this.state.line} onChange={this.handleLine}>
                        {this.lineValues.map(value => {
                            return <option key={value} name={value} value={value}>{value}</option>
                        })}
                    </select>
                </div>
                <XYPlot className="scetterPlot__plot" 
                        height={this.state.height - 200} 
                        width={this.state.width - 100} 
                        margin={{left: 90}} 
                        yType={this.handlType(this.state.toolY, this.state.columnY)} 
                        xType={this.handlType(this.state.toolX, this.state.columnX)}
                        xDomain={this.handlType(this.state.toolX, this.state.columnX) !== 'ordinal' ? [this.minX, this.maxX] : null}
                        yDomain={this.handlType(this.state.toolY, this.state.columnY) !== 'ordinal' ? [this.minY, this.maxY] : null}
                        >
                    <VerticalGridLines yType={this.handlType(this.state.toolY, this.state.columnY)} xType={this.handlType(this.state.toolX, this.state.columnX)}/>
                    <HorizontalGridLines yType={this.handlType(this.state.toolY, this.state.columnY)} xType={this.handlType(this.state.toolX, this.state.columnX)}/>
                    
                    <DecorativeAxis
                        className='middle-line'
                        axisStart={{x: this.state.linear ? 0 : 1, y: this.state.linear ? 0 : 1}}
                        axisEnd={{x: this.maxX, y: this.maxY}}
                        axisDomain={[0, 10000000000]}
                        style={{
                            ticks: {stroke: '#009440', opacity: 0},
                            text: {stroke: 'none', fill: '#009440', fontWeight: 600, opacity: 0}
                        }}
                    />  
                    <DecorativeAxis
                        axisStart={{x: this.state.linear ? 0 : this.state.line, y: this.state.linear ? 0 : 1}}
                        axisEnd={{x: this.maxX*this.state.line, y: this.maxY}}
                        axisDomain={[0, 10000000000]}
                        style={{
                            ticks: {stroke: '#ADDDE1', opacity: 0},
                            text: {stroke: 'none', fill: '#6b6b76', fontWeight: 600, opacity: 0}
                        }}
                    />  
                    <DecorativeAxis
                        axisStart={{x: this.state.linear ? 0 : 1, y: this.state.linear ? 0 : this.state.line}}
                        axisEnd={{x: this.maxX, y: this.maxX*this.state.line}}
                        axisDomain={[0, 10000000000]}
                        style={{
                            ticks: {stroke: '#ADDDE1', opacity: 0},
                            text: {stroke: 'none', fill: '#6b6b76', fontWeight: 600, opacity: 0}
                        }}
                    /> 
                    {this.lineCount === false ? (window.confirm('No correct results, show all results?') ? this.setState({correct: false}) : null) : null}
                    <XAxis title = {this.state.nameX} tickFormat = {value => value} yType={this.handlType(this.state.toolY, this.state.columnY)} xType={this.handlType(this.state.toolX, this.state.columnX)}/>
                    <YAxis title = {this.state.nameY} tickFormat = {value => value} yType={this.handlType(this.state.toolY, this.state.columnY)} xType={this.handlType(this.state.toolX, this.state.columnX)}/>
                    <MarkSeries data={this.dataArray} onValueMouseOver={(datapoint, event) => this.setState({value: datapoint})} onValueMouseOut={(datapoint, event) => this.setState({value: null})}/> 
                    {this.state.value ? <Hint value={this.state.value} /> : null}
                </XYPlot>
                <button className="btn" onClick={this.toggleLinear}>{this.state.linear ? 'Switch to Logarithmic Scale' : 'Switch to Linear Scale'}</button>
                <button className="btn" onClick={this.toggleCorrectResults}>{this.state.correct ? 'Switch to All Results' : 'Switch to Correct Results Only'}</button>
            </div>
        )
    }
}