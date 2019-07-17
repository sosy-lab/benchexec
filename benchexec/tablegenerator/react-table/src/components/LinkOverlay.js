import React from 'react';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faTimes } from '@fortawesome/free-solid-svg-icons'
import JSZip from 'jszip'
// import JSZipUtils from 'jszip-utils'


export default class LinkOverlay extends React.Component {

    constructor(props) {
        super(props);
        this.state = {
            content: 'loading...'
        };
        this.link = this.props.link;
        // this.link="https://sosy-lab.github.io/benchexec/example-table/cbmc.2015-12-11_1211.logfiles/s3_clnt.blast.04_false-unreach-call.i.cil.c.log"
        this.content = 'text'
        this.cachedZipFileEntries = {}
    };

    debug = (logInfo) => {
        if (!true) {
            console.log(logInfo)
        }
      }

    giveUp = (error) => {
        this.setState({
            content:    "Error while loading content (" + error + ").<br>" +
                        "This could be a problem of the <a href='https://en.wikipedia.org/wiki/Same-origin_policy'>same-origin policy</a> of your browser.<br><br>" 
        })
        if (window.location.href.indexOf("file://") === 0) {
            this.setState({
                content: 
                        "Error while loading content (" + error + ").<br>" +
                        "This could be a problem of the <a href='https://en.wikipedia.org/wiki/Same-origin_policy'>same-origin policy</a> of your browser.<br><br>" +        
                        "If you are using Google Chrome, try launching it with a flag --allow-file-access-from-files.<br>" +
                        "Reading files from within ZIP archives on the local disk does not work with Google Chrome,<br>" +
                        "if the target file is within a ZIP archive you need to extract it.<br><br>" +
                        "Firefox can access files from local directories by default,<br>" +
                        "but this does not work for files that are not beneath the same directory as this HTML page.<br><br>"
            });
        }
        this.setState({
            content: 
                        "Error while loading content (" + error + ").<br>" +
                        "This could be a problem of the <a href='https://en.wikipedia.org/wiki/Same-origin_policy'>same-origin policy</a> of your browser.<br><br>" +        
                        "If you are using Google Chrome, try launching it with a flag --allow-file-access-from-files.<br>" +
                        "Reading files from within ZIP archives on the local disk does not work with Google Chrome,<br>" +
                        "if the target file is within a ZIP archive you need to extract it.<br><br>" +
                        "Firefox can access files from local directories by default,<br>" +
                        "but this does not work for files that are not beneath the same directory as this HTML page.<br><br>"+
                        "You can try to download the file: <a href=" + this.link + ">" + this.link + "</a>"
        });
    }

    writeToContentPane = (text) => {
        this.debug(text);
        const newtext = text.replace(/&/g, "&amp;")
                    .replace(/"/g, "&quot;")
                    .replace(/</g, "&lt;")
                    .replace(/>/g, "&gt;");
        this.content = newtext;
    }
    
    loadContent = (url) => {
        this.writeToContentPane("Loading file " + url);
        // var splitPos = url.lastIndexOf('/');
        // var zipUrl = url.substring(0, splitPos) + ".zip";
        // var logfile = decodeURIComponent(url.substring(splitPos));


        fetch(url)
            .then(response => {
                response.text()
                    .then(content => {
                        this.setState({
                            content,
                        });
                    })
                    .catch(e => this.attemptLoadingFromZIP(url));
            })
            .catch(e => this.attemptLoadingFromZIP(url));
    }

    attemptLoadingFromZIP = (url) => {
        console.log('Text is not received. Try as zip?');
        const splitPos = url.lastIndexOf('/');
        const zipUrl = url.substring(0, splitPos) + ".zip";
        const logfile = decodeURIComponent(url.substring(splitPos));

        fetch(zipUrl)       // 1) fetch the url
        .then(function (response) {                       // 2) filter on 200 OK
            if (response.status === 200 || response.status === 0) {
                return Promise.resolve(response.blob());
            } else {
                return Promise.reject(new Error(response.statusText));
            }
        })
        .then(JSZip.loadAsync)                            // 3) chain with the zip promise
        .then((zip) => zip.file(logfile).async("string")) // 4) chain with the text content promise
        .then((content) => {                    // 5) display the result
            this.setState({ content });
        }, (error) => {
            console.log('ERROR receiving ZIP', error);
            this.setState({ content: error });
        });
    }

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

    render() {
        this.loadContent(this.link);
        return (
            <div className="overlay">
                <FontAwesomeIcon icon={faTimes} onClick={this.props.close} className="closing" />
                <pre>{this.state.content}</pre>
                <input />
            </div>
        )
    }
}