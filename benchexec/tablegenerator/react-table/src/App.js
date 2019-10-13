import "./App.scss";
import React, { Component } from "react";
import Overview from "./components/Overview";

class App extends Component {
  render() {
    return (
      <div className="App">
        <main>
          <Overview />
          {/* imports the component Overview with all subcomponents */}
        </main>
        <footer className="App-footer"></footer>
      </div>
    );
  }
}

export default App;
