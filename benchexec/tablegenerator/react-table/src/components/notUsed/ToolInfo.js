import React from 'react';
import { withFixedColumnsScrollEvent } from 'react-table-hoc-fixed-columns';
// import InfoEntry from './InfoEntry';
export default class ToolInfo extends React.Component {
    constructor(props) {
        super(props);
        //binding
        //methods
        this.renderColumns = this.renderColumns.bind(this);
    };
    renderColumns (key, value) {
        return value.content.map((item, index) => {
            return <td key={key+index} colSpan={item[1]}>{item[0]}</td>
        });
    }
    render() {
        const tableHeader=this.props.tableHeader;
        let toolInfo = Object.entries(tableHeader).map(([key, value])=> {
            return ((value && value && key !== 'title') ? <tr key={key}><td key={key+value}><strong>{key}:</strong></td>{this.renderColumns(key, value)}</tr> : null)
        });
        

        //-------------------Hierfür bin ich heute zu dumm----------------------------

        // let lines = ['displayName', 'date', 'limit'];
        
        //  let toolInfoSorted = lines.forEach((line) => {
        //         console.log(tableHeader.line);
            
        //     return line;
        // });
        // let toolInfoSorted = Object.entries(tableHeader).forEach(([key, value])=> {
        //     value ? console.log(value) : console.log(key)

        // });
            // return (value ? <tr key="displayName"><td key="displayName"><strong>"displayName":</strong></td><td key={displayName.value}>{displayName.value}</td></tr> : null)

        return (
            <>
            <table className="toolInfo">
                <tbody>
                    {toolInfo}
                </tbody>
            </table>
            </>
        )
    }
}