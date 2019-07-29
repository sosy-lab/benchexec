import React from 'react';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faTimes } from '@fortawesome/free-solid-svg-icons'
import JSZip from 'jszip'
// import JSZipUtils from 'jszip-utils'


export default class LinkOverlay extends React.Component {

    constructor(props) {
        super(props);
        this.state = {
            content: `loading file: ${this.props.link}`,
        };
        this.cachedZipFileEntries = {}

        this.loadContent(this.props.link);
    };

    loadContent = (url) => {
        console.log('load content', url);
        if(url) {
            fetch(url)
                .then(response => {
                    //status 404/403 => Fehler?
                    if (response.status === 200 || response.status === 0) {
                        response.text()
                            .then(content => {
                                this.setState({ content });
                            })
                            .catch(e => {
                                console.log('Error: Stream not readable', url, e);
                                this.attemptLoadingFromZIP(url);
                            });
                    } else {
                        console.log('Error: Loading file not possible', response);
                        this.attemptLoadingFromZIP(url);
                    }
                })
                .catch(e => {
                    console.log('Error: Resource not found', url, e);
                    this.attemptLoadingFromZIP(url);
                });
        }
    }

    attemptLoadingFromZIP = (url) => {
        console.log('Text is not received. Try as zip?', url);
        const splitPos = url.lastIndexOf('/');
        const zipUrl = url.substring(0, splitPos) + ".zip";
        const urlArray = url.split('/');
        const logfile = decodeURIComponent(`${urlArray[urlArray.length - 2]}/${urlArray[urlArray.length - 1]}`); // <folder>/<logfile>

        fetch(zipUrl)                                           // 1) fetch the url
            .then((response) => 
                (response.status === 200 || response.status === 0) ? // 2) filter on 200 OK
                    Promise.resolve(response.blob()) :    //=> then-case
                    Promise.reject(new Error(response.statusText)) //=> ERROR-case  
            )
            .then(JSZip.loadAsync)                              // 3) chain with the zip promise
            .then((zip) => zip.file(logfile).async("string"))   // 4) chain with the text content promise
            .then((content) => {                                // 5) display the result
                this.setState({ content });
            }, (error) => {
                console.log('ERROR receiving ZIP', error);
                this.setState({ error: `${error}` });
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
        return (
            <div className="overlay">
                <FontAwesomeIcon icon={faTimes} onClick={this.props.close} className="closing" />
                {
                    !this.state.error ? (
                        <>
                            <pre>{this.state.content}</pre>
                            <input />
                        </>
                    ) : (
                        <div>
                            <p>Error while loading content ({this.state.error}).</p>
                            <p>This could be a problem of the <a href='https://en.wikipedia.org/wiki/Same-origin_policy'>same-origin policy</a> of your browser.</p>
                            {
                                window.location.href.indexOf("file://") === 0 ? 
                                    <>
                                        <p>If you are using Google Chrome, try launching it with a flag --allow-file-access-from-files.</p>
                                        <p>Reading files from within ZIP archives on the local disk does not work with Google Chrome, if the target file is within a ZIP archive you need to extract it.</p>
                                        <p>Firefox can access files from local directories by default, but this does not work for files that are not beneath the same directory as this HTML page.</p>
                                    </> : 
                                    null
                            }
                            <p>You can try to download the file: <a href={this.props.link}>{this.props.link}</a></p>
                        </div>
                    )
                }
            </div>
        )
    }
}