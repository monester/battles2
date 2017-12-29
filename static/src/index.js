import React from 'react';
import ReactDOM from 'react-dom';
import './bootstrap.min.css'
import './bootstrap-theme.min.css'
import FontAwesomeIcon from '@fortawesome/react-fontawesome'
import { faSpinner } from '@fortawesome/fontawesome-free-solid'

let moment = require('moment-timezone');


class NavBar extends React.Component {
  render() {
    let status;
    if (this.props.loading) {
      status = <FontAwesomeIcon icon={faSpinner} spin />
    }

    return <nav className="navbar  navbar-defautl">
      <div className="container-fluid">
        <div className="navbar-header">
          <span className="navbar-brand">Clan Battles</span>
          <div className="navbar-form navbar-left">
            <div className="form-group">
              <input type="text" className="form-control"
                onChange={event => {this.props.onClanTagChange(event.target.value)} }
                onKeyPress={event => {if(event.key === 'Enter'){this.props.refreshHandler()}}}
                value={this.props.clanTag}
              />
            </div>
            <button className="btn btn-default" onClick={this.props.refreshHandler}>Show {status}</button>
            <button className="btn btn-default" onClick={this.props.refreshAllHandler}>Sync all data</button>
          </div>
          <div className="navbar-form navbar-left">{this.props.statusMessage}</div>
        </div>
      </div>
    </nav>
  }
}

class ProvinceRowCell extends React.Component {
  render() {
    const round = this.props.round;
    const clanTag = this.props.clanTag;
    if(round) {
      let versus = "";
      if(round.clan_a && round.clan_b) {
        versus = ((round.clan_a.tag === clanTag)?round.clan_b:round.clan_a).tag
      } else if(round.clan_a) {
        versus = round.clan_a.tag
      } else if(round.clan_b) {
        versus = round.clan_b.tag
      }
      return (
        <td className="btn-default"><div className="cell">{round.title} {versus}</div></td>
      )
    }
    return <td><div className="cell" /></td>
  }
}

class ProvinceRow extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      tags: []
    }
  }

  componentDidMount() {

  }
  render() {
    const cells = [];
    const province_id = this.props.province.province_id;
    const province_name = this.props.province.province_name;
    const prime_time = this.props.province.prime_time;
    const arena_name = this.props.province.arena_name;
    const server = this.props.province.server;
    this.props.times.forEach(key => {
      cells.push(
        <ProvinceRowCell
          key={this.props.province.province_id + key}
          clanTag={this.props.clanTag}
          round={this.props.province.rounds[key]} />
      )
    });
    return (
      <tr>
        <th className="headcol">
          <a href={"https://ru.wargaming.net/globalmap/#province/" + province_id}>
            {server} {province_name} {prime_time.format("HH:mm")} {arena_name}</a>
          </th>
        <td>{this.props.province.mode}</td>
        {cells}
      </tr>
    )
  }
}

class TimeTable extends React.Component {
  constructor(props) {
    super(props);
    this.state = {tableWidth: 0}
  }

  updateDimensions = () => { this.setState({tableWidth: (document.body.clientWidth - 350) + 'px'}) };
  componentDidMount() { window.addEventListener("resize", this.updateDimensions); }
  componentWillMount() { this.updateDimensions(); }
  componentWillUnmount() { window.removeEventListener("resize", this.updateDimensions); }

  render() {
    const allTimes = new Set();
    this.props.provinces.forEach(province => {
      Object.keys(province.rounds).forEach(key => { allTimes.add(key) })
    });

    const timesRow = [];
    const times = [];
    const now = moment().subtract(1800000);
    Array.from(allTimes).sort().forEach(timeStr => {
      const time = moment(timeStr);
      if(! this.props.onlyActive || time > now) {
        times.push(timeStr);
        timesRow.push(<th key={"time"+time}><div className="cell">{time.format("HH:mm")}</div></th>)
      }
    });

    const provinces = this.props.provinces.sort((a, b) => {
      let key_a =  [
        [15, 45].includes(a.prime_time.minutes()),
        - a.prime_time.toDate()
      ];
      let key_b =  [
        [15, 45].includes(b.prime_time.minutes()),
        - b.prime_time.toDate()
      ];
      return (key_a > key_b)?1:-1
    }).map(province =>{
      return <ProvinceRow
        key={province.province_id}
        province={province}
        times={times}
        clanTag={this.props.clanTag} />
    });
    if (this.props.clanTag !== '') {
      return (
        <div className="timetable" style={{width: this.state.tableWidth}}>
          <table className="table">
            <tbody>
              <tr>
                <th className='headcol'>Province name</th>
                <th>Attack type</th>
                {timesRow}
              </tr>
              {provinces}
            </tbody>
          </table>
        </div>
      )
    } else if(this.props.loading) {
      return (
        <div style={{width: this.state.tableWidth, textAlign: 'center'}}>
          <h1>Loading...</h1>
        </div>
      )
    } else {
      return (
        <div style={{width: this.state.tableWidth, textAlign: 'center'}}>
          <h1><a href="#LECAT">LECAT</a></h1>
          <h1><a href="#SMIRK">SMIRK</a></h1>
        </div>
      )
    }
  }
}

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
      provinces.forEach(province => {
        const roundsMap = new Map();
        province.rounds.forEach(round => {
          round.time = moment(round.time);
          const timeKey = round.time.clone().tz('UTC');
          if([15, 45].includes(round.time.minutes())) {
            timeKey.subtract(900000)
          }
          roundsMap[timeKey.format('YYYY-MM-DDTHH:mm:ss') + 'Z'] = round
        });
        const prime_time = province.prime_time.split(":");
        province.prime_time = moment().hour(parseInt(prime_time[0], 10) + moment().utcOffset() / 60).minute(prime_time[1]).second(0);
        province.rounds = roundsMap
      });
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
