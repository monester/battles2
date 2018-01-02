import React from 'react';
import ReactDOM from 'react-dom';
import NavBar from './top.js'
import TimeTable from './table.js';
import moment from 'moment-timezone'

import 'bootstrap/dist/css/bootstrap.css';
import 'bootstrap/dist/css/bootstrap-reboot.css';

import './css.css'


class App extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      clanTag: window.location.hash.substr(1),
      loadedClanTag: '',
      loading: false,
      onlyActive: true,
      provinces: [],
      status: '',
    }
  }

  refreshTableHandler = () => {
    window.location.hash = "#" + this.state.clanTag;
    this.setState({loading: true});
    // fetch data and normalize it
    fetch('http://localhost:8000/update/' + this.state.clanTag).then(response => {
      return response.json();
    }).then(data => {
      const provinces = data.provinces;
      this.setState({
        loading: false,
        loadedClanTag: this.state.clanTag,
        provinces: data.provinces,
      })
    }).catch(() => {
      this.setState({
        loading: false,
        loadedClanTag: this.state.clanTag,
        provinces: [],
      })
    })
  };

  onClanTagChange = (clanTag) => {
    this.setState({clanTag: clanTag.toUpperCase()})
  };

  componentWillMount() {
    this.refreshTableHandler()
  }

  componentDidMount() {
     window.addEventListener("hashchange", e => {
      this.setState({clanTag: window.location.hash.substr(1)});
      setTimeout(this.refreshHandler, 0)
     });
  }

  refreshAllHandler = () => {
    let component = this;
    let position = 0;
    let xhr = new XMLHttpRequest();
    xhr.open("GET", "http://localhost:8000/update_all/", true);
    xhr.onprogress = function (e) {
      component.setState({status: xhr.responseText.substr(position)});
      position = e.loaded
    };
    xhr.send()
  };

  render() {
    const clanTag = this.state.clanTag;
    const loadedClanTag = this.state.loadedClanTag;
    const loading = this.state.loading;
    const status = this.state.status;

    return (
      <div>
        <NavBar
          clanTag={clanTag}
          loading={loading}
          onClanTagChange={this.onClanTagChange}
          refreshHandler={this.refreshTableHandler}
          refreshAllHandler={this.refreshAllHandler}
          statusMessage={status} />

        <TimeTable
          clanTag={loadedClanTag}
          loading={loading}
          onlyActive={this.state.onlyActive}
          provinces={this.state.provinces} />
      </div>
    )
  }
}

ReactDOM.render(<App />, document.getElementById('root'));
