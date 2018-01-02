import React from 'react';
import moment from 'moment-timezone'


class Cell extends React.Component {
  render() {
    const round = this.props.round;
    const currentTime = this.props.currentTime;
    const roundTime = new Date(round['time']);
    const tag = round['clan_a']?round['clan_a']['tag']:"";
    console.log(roundTime / 10000 - currentTime);
    const style = {
      position: 'absolute',
      left: roundTime / 10000 - currentTime,
      border: '0px dashed #000',
      width: '180px',
      height: '50px',
      backgroundColor: '#E4F0F5',
      fontSize: '10px',
    };
    // console.log(round);
    let versus = "";
    // if(round.clan_a && round.clan_b) {
    //   versus = ((round.clan_a.tag === clanTag)?round.clan_b:round.clan_a).tag
    // } else if(round.clan_a) {
    //   versus = round.clan_a.tag
    // }
    const date = new Date(roundTime * 10000).toString();
    return (
      <div style={style}>{date} {tag}</div>
    )
  }
}


class Row extends React.Component {
  render() {
    const province_id = this.props.province['province_id'];
    const province_name = this.props.province['province_name'];
    const prime_time = this.props.province['prime_time'];

    const currentMargin = this.props.currentMargin;
    const currentTime = this.props.currentTime;
    this.props.province.rounds.forEach(e => {
      console.log(e)
    });
    const cells = this.props.province.rounds.map(round =>
      <Cell key={province_id+round['time']} round={round} currentTime={currentTime} />
    );
    const titleStyle = {
      marginLeft: '0px',
      position: 'absolute',
      left: '0',
    };
    const outerStyle = {
      overflow: 'hidden',
    };
    const innerStyle = {
      position: 'relative',
      height: '50px',
      marginLeft: (currentMargin * 50) + 'px',
    };
    return (
      <div>
        <div style={titleStyle}>
          <a href={"https://ru.wargaming.net/globalmap/#province/" + province_id}>
          {province_name} {prime_time}
          </a>
        </div>
        <div style={outerStyle}>
          <div style={innerStyle}>
            {cells}
          </div>
        </div>
      </div>
    )
  }
}

class TimeTable extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      tableWidth: 0,
      currentTime: new Date() / 10000,
      currentMargin: 0,
    }
  }

  updateDimensions = () => { this.setState({tableWidth: (document.body.clientWidth - 350) + 'px'}) };
  componentDidMount() { window.addEventListener("resize", this.updateDimensions); }
  componentWillMount() { this.updateDimensions(); }
  componentWillUnmount() { window.removeEventListener("resize", this.updateDimensions); }

  render() {
    // const allTimes = new Set();
    // this.props.provinces.forEach(province => {
    //   Object.keys(province.rounds).forEach(key => { allTimes.add(key) })
    // });
    //
    // const timesRow = [];
    // const times = [];
    // const now = moment().subtract(1800000);
    // Array.from(allTimes).sort().forEach(timeStr => {
    //   const time = moment(timeStr);
    //   if(! this.props.onlyActive || time > now) {
    //     times.push(timeStr);
    //     timesRow.push(<th key={"time"+time}><div className="cell">{time.format("HH:mm")}</div></th>)
    //   }
    // });

    // const provinces = this.props.provinces.sort((a, b) => {
    //   // let key_a =  [
    //   //   [15, 45].includes(a.prime_time.minutes()),
    //   //   - a.prime_time.toDate()
    //   // ];
    //   // let key_b =  [
    //   //   [15, 45].includes(b.prime_time.minutes()),
    //   //   - b.prime_time.toDate()
    //   // ];
    //   // return (key_a > key_b)?1:-1
    //   return 1
    // }).map(province =>{
    //   return <ProvinceRow
    //     key={province.province_id}
    //     province={province}
    //     times={times}
    //     clanTag={this.props.clanTag} />
    // });
    if(this.props.loading) {
      return (
        <div style={{width: this.state.tableWidth, textAlign: 'center'}}>
        <h1>Loading...</h1>
        </div>
      )
    } else {
      const currentTime = this.state.currentTime;
      const currentMargin = this.state.currentMargin;
      const rows = this.props.provinces.map( province =>
        <Row key={province['province_id']}
             currentTime={currentTime}
             currentMargin={currentMargin}
             province={province} />
      );
      const style = {
        width: '600px',
        border: '1px solid #000',
        marginLeft: '200px',
      };
      return (
        <div>
          <div style={style}>
            {rows}
          </div>
        </div>
      )
    }
  }
}

export default TimeTable;
