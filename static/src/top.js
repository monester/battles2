import React from "react";
import FontAwesomeIcon from '@fortawesome/react-fontawesome'
import { faSpinner } from '@fortawesome/fontawesome-free-solid'

class NavBar extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      flagEditClan: false
    }
  }

  render() {
    let status;
    if(this.props.loading) {
      status = <FontAwesomeIcon icon={faSpinner} spin />
    }

    return (
      <nav className="navbar navbar-expand-lg navbar-light bg-light">
        <a className="navbar-brand" href={"/#" + this.props.clanTag} onClick={this.props.refreshHandler}>Clan Battles</a>
        <button className="navbar-toggler" type="button" data-toggle="collapse" data-target="#navbarSupportedContent" aria-controls="navbarSupportedContent" aria-expanded="false" aria-label="Toggle navigation">
          <span className="navbar-toggler-icon" />
        </button>
        <div className="collapse navbar-collapse" id="navbarSupportedContent">
          <form className="form-inline my-2 my-lg-0">
            <input className="form-control mr-sm-2" type="search" placeholder="Clan Tag" aria-label="Clan Tag"
                   onChange={event => {this.props.onClanTagChange(event.target.value)} }
                   onKeyPress={event => {if(event.key === 'Enter'){this.props.refreshHandler()}}}
                   value={this.props.clanTag}
            />
            <button className="btn my-2 my-sm-0" style={{width: '100px'}} onClick={this.props.refreshHandler}>Show&nbsp;{status}</button>
          </form>
        </div>
      </nav>
    )
  }
}

export default NavBar
