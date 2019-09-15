import React from 'react';
export default class Reset extends React.Component {
    render() {
        return (
            <button className="reset" onClick={this.props.resetFilters}>Reset Filters</button>
        )
    }
}