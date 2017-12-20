import React from 'react';
import ReactDOM from 'react-dom';
var moment = require('moment-timezone');


class NavBar extends React.Component {
  render() {
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
            <button className="btn btn-default" onClick={this.props.refreshHandler}>Show</button>
          </div>
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
      var versus = ""
      if(round.clan_a && round.clan_b) {
         versus = ((round.clan_a === clanTag)?round.clan_b:round.clan_a).tag
      }
      return (
        <td className="btn-default"><div className="cell">{round.title} {versus}</div></td>
      )
    }
    return <td><div className="cell"></div></td>
  }
}

class ProvinceRow extends React.Component {
  render() {
    const cells = []
    this.props.times.forEach(key => {
      cells.push(
        <ProvinceRowCell
          key={this.props.province.province_id + key}
          clan={this.props.clanTag}
          round={this.props.province.rounds[key]} />
      )
    })
    return (
      <tr>
        <th className="headcol">
          <a href={"https://ru.wargaming.net/globalmap/#province/" + this.props.province.province_id}>
            {this.props.province.province_name} {this.props.province.prime_time.format("HH:mm")}</a>
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

  updateDimensions = () => { this.setState({tableWidth: (document.body.clientWidth - 200) + 'px'}) }
  componentDidMount() { window.addEventListener("resize", this.updateDimensions); }
  componentWillMount() { this.updateDimensions(); }
  componentWillUnmount() { window.removeEventListener("resize", this.updateDimensions); }

  render() {
    var times = new Set()
    this.props.provinces.forEach(province => {
      Object.keys(province.rounds).forEach(key => { times.add(key) })
    })
    times = Array.from(times).sort()

    const timesRow = []
    times.sort().forEach(timeStr => {
      const time = moment(timeStr)
      timesRow.push(<th key={"time"+time}><div className="cell">{time.format("HH:mm")}</div></th>)
    })

    const provinces = this.props.provinces.sort((a, b) => {
      var key_a =  [
        [15, 45].includes(a.prime_time.minutes()),
        - a.prime_time.toDate()
      ]
      var key_b =  [
        [15, 45].includes(b.prime_time.minutes()),
        - b.prime_time.toDate()
      ]
      return (key_a > key_b)?1:-1
    }).map(province =>{
      return <ProvinceRow
        key={province.province_id}
        province={province}
        times={times}
        clanTag={this.props.clanTag} />
    })
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
    super(props)
    this.state = {
      clanTag: window.location.hash.substr(1),
      loadedClanTag: '',
      loading: false,
      provinces: [],
    }
  }

  refreshHandler = () => {
    window.location.hash = "#" + this.state.clanTag
    fetch('http://127.0.0.1:8000/update/' + this.state.clanTag).then(response => {
      return response.json();
    }).then(data => {
      const provinces = data.provinces
      provinces.forEach(province => {
        const roundsMap = new Map()
        province.rounds.forEach(round => {
          round.time = moment(round.time)
          const timeKey = round.time.clone().tz('UTC')
          if([15, 45].includes(round.time.minutes())) {
            timeKey.subtract(900000)
          }
          roundsMap[timeKey.format('YYYY-MM-DDTHH:mm:ss') + 'Z'] = round
        })
        province.prime_time = province.rounds[0].time
        province.rounds = roundsMap
      })
      this.setState({
        loadedClanTag: this.state.clanTag,
        provinces: data.provinces,
      })
    })
  }

  onClanTagChange = (clanTag) => {
    this.setState({clanTag: clanTag})
  }

  componentWillMount() {
    this.refreshHandler()
  }

  render() {
    const clanTag = this.state.clanTag
    const loadedClanTag = this.state.loadedClanTag
    const loading = this.state.loading

    return (
      <div>
        <NavBar
          clanTag={clanTag}
          onClanTagChange={this.onClanTagChange}
          refreshHandler={this.refreshHandler} />

        <TimeTable
          clanTag={loadedClanTag}
          loading={loading}
          provinces={this.state.provinces} />
      </div>
    )
  }
}

ReactDOM.render(<App />, document.getElementById('root'));
