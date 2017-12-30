import React from "react";
import FontAwesomeIcon from '@fortawesome/react-fontawesome'
import { faSpinner } from '@fortawesome/fontawesome-free-solid'

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

export default NavBar
