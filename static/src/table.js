import React from 'react';
import moment from 'moment-timezone'

import './css.css'

const rowHeight = 60;
const cellWidth = 180;
const titleWidth = 300;

const tzOffset = new Date().getTimezoneOffset();


class Cell extends React.Component {
  render() {
    const round = this.props.round;
    const currentTime = this.props.currentTime;
    const roundTime = moment(round['time']);
    const tagClanA = round['clan_a']?round['clan_a']['tag']:'';
    const tagClanB = round['clan_b']?round['clan_b']['tag']:'';
    const tag = (this.props.clanTag === tagClanA)?tagClanB:tagClanA;
    console.log(round);
    const style = {
      marginBottom: '3px',
      borderLeft: '1px solid #dcdcdc',
      position: 'absolute',
      left: (roundTime - currentTime) / 10000,
      width: (cellWidth + 1) + 'px',
      height: (rowHeight + 1) + 'px',
      backgroundColor: '#E4F0F5',
      fontSize: '10px',
    };
    let versus = "";
    const date = roundTime.format("HH:mm");
    return (
      <div style={style}>{date} {tag}</div>
    )
  }
}


class Row extends React.Component {
  render() {
    const provinceId = this.props.province['province_id'];
    const provinceName = this.props.province['province_name'];
    const primeTime = this.props.province['prime_time'].split(":").map((value, index) => {
      let tz;
      switch(index) {
        case 0:
          tz = value - Math.floor(tzOffset / 60);
          break;
        case 1:
          tz = value - tzOffset % 60;
          break;
        default:
          return
      }
      return (tz < 10)?("0" + tz):("" + tz)
    }).filter(e=>e).join(":");

    const currentMargin = this.props.currentMargin;
    const currentTime = this.props.currentTime;
    const cells = this.props.province.rounds.map(round =>
      <Cell key={provinceId + round['time']}
            round={round}
            currentTime={currentTime}
            clanTag={this.props.clanTag} />
    );
    const titleStyle = {
      marginLeft: '0',
      marginRight: '0',
      position: 'absolute',
      left: '0',
      width: titleWidth + 'px',
      height: rowHeight + 'px',
      overflow: 'hidden',
      padding: '2px 0px 2px 10px',
      borderRight: '1px solid'
    };
    const outerStyle = {
      overflow: 'hidden',
      marginLeft: titleWidth + 'px',
    };
    const innerStyle = {
      position: 'relative',
      height: (rowHeight + 3) + 'px',
      marginLeft: (currentMargin * 50) + 'px',
    };
    return (
      <div style={{marginLeft: "-" + titleWidth + "px"}} className="province-row">
        <div style={titleStyle}>
          <span style={{width: '40px', float: 'left'}}>RU1</span>
          <span style={{width: '180px', float: 'left'}}>
            <a href={"https://ru.wargaming.net/globalmap/#province/" + provinceId}>
              {provinceName}
            </a>
          </span>
          <span style={{width: '50px', float: 'right'}}>{primeTime}</span>
          <div className="input-group input-group-sm mb-3">
            <input type="text" className="form-control" />
          </div>
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
    const currentTime = moment().seconds(0);
    // by default show 1 hour before now
    currentTime.subtract(currentTime.minutes() % 30, 'minute');
    console.log(currentTime.format());
    this.state = {
      currentTime: currentTime,
      currentMargin: 0,
    }
  }

  render() {
    if(this.props.loading) {
      return (
        <div style={{width: '100%', textAlign: 'center'}}>
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
             province={province}
             clanTag={this.props.clanTag} />
      );
      const style = {
        width: 'calc(100% - ' + titleWidth + ')',
        border: '0px solid #000',
        marginLeft: titleWidth + 'px',
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
