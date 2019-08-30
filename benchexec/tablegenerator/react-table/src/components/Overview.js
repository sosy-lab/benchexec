import React from 'react';
import { Tab, Tabs, TabList, TabPanel } from 'react-tabs';
import "react-tabs/style/react-tabs.css";
import Table from './ReactTable.js';
import Summary from './Summary.js';
import Info from './Info.js';
import SelectColumn from './SelectColumn.js';
import ScatterPlot from './ScatterPlot.js';
import QuantilePlot from './QuantilePlot.js';
import LinkOverlay from './LinkOverlay.js';

//example date for development
if (process.env.NODE_ENV !== 'production') {
    window.data = require('../data/data.json');
}

// console.log('table data', window.data);

export default class Overview extends React.Component {
    constructor(props) {
        super(props);
        this.tableHeader = window.data.head;
        this.tools = window.data.tools.map(tool => ({
            ...tool, 
            isVisible: true, 
            columns: tool.columns.map(c => ({ ...c, isVisible: true }))
        }));
        this.columns = window.data.tools.map(t => t.columns.map(c => c.title));
        this.data = window.data.rows;
        this.stats = window.data.stats;
        this.properties = window.data.props;
        this.filtered = [];
        
        this.state = {
            showSelectColumns: false,
            showLinkOverlay: false,
            columns: this.columns,
            tools: this.tools,
            table: this.data,
            filtered: [],
            tabIndex: 0,
            quantilePreSelection: this.tools[0].columns[1],
        }
        // this.filterRowId();
    };

// -----------------------SelectColumns-----------------------
    toggleSelectColumns = () => {
        this.setState(prevState => ({ 
            showSelectColumns: !prevState.showSelectColumns,
        }));
    }
    
// -----------------------Link Overlay-----------------------
    toggleLinkOverlay = (ev, hrefRow) => {
        ev.preventDefault();
        
        this.setState(prevState => ({ 
            showLinkOverlay: !prevState.showLinkOverlay,
            link: hrefRow,
        }));
    }

// -----------------------Filter-----------------------
    setFilter = (filteredData) => {
        this.filteredData = filteredData.map(row => {
            return row._original;
        });
    }
    filterPlotData = (filter) => {
       this.setState({
           table: this.filteredData,
           filtered: filter
       })
    }
    resetFilters = () => {
        this.setState({
            table: this.data,
            filtered: []
        })
    }

// -----------------------Common Functions-----------------------
    getRunSets = (runset) => {
        return `${runset.tool} ${runset.date} ${runset.niceName}`
    }  

    prepareTableValues = (el, tool, column, href, row) => {
        const col = this.tools[tool].columns[column];
        if (col.type.name === "main_status" || col.type.name === "status") {
            return el.formatted ? <a href={href} className={row.category} onClick={href ? ev => this.toggleLinkOverlay(ev, href) : null} title="Click here to show output of tool">{el.formatted}</a> : null
        } else {
            return el;
        }
    }

    changeTab = (_, column, tab) => {
        this.setState({
            tabIndex: tab,
            quantilePreSelection: column,
        })
    } 

    render() {
        return (
            <div className="App">
            <main>
                <div className="overview">
                    <Tabs selectedIndex={this.state.tabIndex} onSelect={tabIndex => this.setState({ tabIndex, showSelectColumns: false, showLinkOverlay: false })}>
                        <TabList>
                            <Tab>Summary</Tab>
                            <Tab> Table ({this.state.table.length})</Tab>
                            <Tab> Quantile Plot </Tab>
                            <Tab> Scatter Plot </Tab>
                            <Tab> Info </Tab>
                            {!this.state.filtered.length && <button className="reset" onClick={this.resetFilters}>Reset Filters</button>}
                        </TabList>
                        <TabPanel>
                            <Summary    
                                tools={this.state.tools}
                                tableHeader={this.tableHeader}
                                selectColumn={this.toggleSelectColumns}
                                stats = {this.stats}
                                prepareTableValues = {this.prepareTableValues}
                                getRunSets={this.getRunSets}
                                changeTab= {this.changeTab} />
                        </TabPanel>
                        <TabPanel>
                            <Table      
                                tableHeader={this.tableHeader}
                                data={this.data}
                                tools={this.state.tools}
                                properties={this.properties}
                                selectColumn={this.toggleSelectColumns}
                                getRunSets={this.getRunSets}
                                prepareTableValues = {this.prepareTableValues}
                                setFilter = {this.setFilter}
                                filterPlotData = {this.filterPlotData}
                                filtered = {this.state.filtered}
                                toggleLinkOverlay={this.toggleLinkOverlay}
                                changeTab= {this.changeTab} />
                        </TabPanel>
                        <TabPanel>
                            <QuantilePlot 
                                table={this.state.table}
                                tools={this.state.tools}
                                preSelection={this.state.quantilePreSelection}
                                getRunSets={this.getRunSets} />
                        </TabPanel>
                        <TabPanel>
                            <ScatterPlot 
                                table={this.state.table}
                                columns={this.columns}
                                tools={this.state.tools}
                                getRunSets={this.getRunSets}
                                />
                        </TabPanel>
                        <TabPanel>
                            <Info
                                selectColumn={this.toggleSelectColumns}
                            >
                            </Info>
                        </TabPanel>
                    </Tabs>
                </div>
                <div> 
                    {this.state.showSelectColumns && <SelectColumn 
                                                    close={this.toggleSelectColumns}
                                                    select={this.selectColumns}
                                                    currColumns = {this.state.columns}
                                                    tableHeader = {this.tableHeader}
                                                    getRunSets={this.getRunSets}
                                                    tools={this.state.tools} />}
                    {this.state.showLinkOverlay && <LinkOverlay 
                                                    close={this.toggleLinkOverlay}
                                                    link={this.state.link}
                                                    toggleLinkOverlay={this.toggleLinkOverlay} /> } 
                </div>
            </main>
            </div>
        );
    }
}

  