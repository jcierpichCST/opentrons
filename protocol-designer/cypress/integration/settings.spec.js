describe('The Settings Page', () => {
  before(() => {
    cy.visit('/')
    localStorage.setItem('root.featureFlags.flags', '{"PRERELEASE_MODE":true}')
  })

  it('displays the announcement modal and clicks "GOT IT!" to close it', () => {
    cy.closeAnnouncementModal()
  })

  it('contains a working settings button', () => {
    cy.get("button[class*='navbar__tab__']")
      .contains('Settings')
      .click()
    cy.contains('App Settings')
  })

  it('contains an information section', () => {
    cy.get('h3')
      .contains('Information')
      .should('exist')
  })

  it('contains version information', () => {
    cy.contains('Protocol Designer Version').should('exist')
  })

  it('contains a hints section', () => {
    cy.get('h3')
      .contains('Hints')
      .should('exist')
  })

  it('contains a privacy section', () => {
    cy.get('h3')
      .contains('Privacy')
      .should('exist')
  })

  it('contains a share settings button in the pivacy section', () => {
    // It's toggled off by default
    cy.contains('Share sessions')
      .next()
      .should('have.attr', 'class')
      .and('match', /toggled_off/)
    // Click it
    cy.contains('Share sessions')
      .next()
      .click()
    // Now it's toggled on
    cy.contains('Share sessions')
      .next()
      .should('have.attr', 'class')
      .and('match', /toggled_on/)
    // Click it again
    cy.contains('Share sessions')
      .next()
      .click()
    // Now it's toggled off again
    cy.contains('Share sessions')
      .next()
      .should('have.attr', 'class')
      .and('match', /toggled_off/)
  })

  it('contains an experimental settings section', () => {
    cy.get('h3')
      .contains('Experimental Settings')
      .should('exist')
  })

  it("contains a 'enable multi gen2 pipettes' button in the pivacy section", () => {
    // It's toggled off by default
    cy.contains('Enable multi')
      .next()
      .should('have.attr', 'class')
      .and('match', /toggled_off/)
    // Click it
    cy.contains('Enable multi')
      .next()
      .click()
    // We have to confirm this one
    cy.contains('Switching on an experimental feature').should('exist')
    cy.get('button')
      .contains('Cancel')
      .should('exist')
    cy.get('button')
      .contains('Continue')
      .should('exist')
    // Abort!
    cy.get('button')
      .contains('Cancel')
      .click()
    // Still toggled off
    cy.contains('Enable multi')
      .next()
      .should('have.attr', 'class')
      .and('match', /toggled_off/)
    // Click it again and confirm
    cy.contains('Enable multi')
      .next()
      .click()
    cy.get('button')
      .contains('Continue')
      .click()
    // Now it's toggled on
    cy.contains('Enable multi')
      .next()
      .should('have.attr', 'class')
      .and('match', /toggled_on/)
    // Click it again
    cy.contains('Enable multi')
      .next()
      .click()
    // We have to confirm to turn it off?
    // TODO That doesn't seem right...
    cy.get('button')
      .contains('Continue')
      .click()
    // Now it's toggled off again
    cy.contains('Enable multi')
      .next()
      .should('have.attr', 'class')
      .and('match', /toggled_off/)
  })

  it("contains a 'disable module placement restrictions' toggle in the experimental settings card", () => {
    // It's toggled off by default
    cy.contains('Disable module')
      .next()
      .should('have.attr', 'class')
      .and('match', /toggled_off/)
    // Click it
    cy.contains('Disable module')
      .next()
      .click()
    // We have to confirm this one
    cy.contains('Switching on an experimental feature').should('exist')
    cy.get('button')
      .contains('Cancel')
      .should('exist')
    cy.get('button')
      .contains('Continue')
      .should('exist')
    // Abort!
    cy.get('button')
      .contains('Cancel')
      .click()
    // Still toggled off
    cy.contains('Disable module')
      .next()
      .should('have.attr', 'class')
      .and('match', /toggled_off/)
    // Click it again and confirm
    cy.contains('Disable module')
      .next()
      .click()
    cy.get('button')
      .contains('Continue')
      .click()
    // Now it's toggled on
    cy.contains('Disable module')
      .next()
      .should('have.attr', 'class')
      .and('match', /toggled_on/)
    // Click it again
    cy.contains('Disable module')
      .next()
      .click()
    // We have to confirm to turn it off
    cy.get('button')
      .contains('Continue')
      .click()
    // Now it's toggled off again
    cy.contains('Disable module')
      .next()
      .should('have.attr', 'class')
      .and('match', /toggled_off/)
  })

  it('remembers when we enable things', () => {
    // Enable a button
    // We're not using the privacy button because that
    // interacts with analytics libraries, which might
    // not be accessible in a headless environment
    cy.contains('Enable multi')
      .next()
      .click()
    cy.get('button')
      .contains('Continue')
      .click()
    // Leave the settings page
    cy.get("button[class*='navbar__tab__']")
      .contains('FILE')
      .click()
    // Go back to settings
    cy.get("button[class*='navbar__tab__']")
      .contains('Settings')
      .click()
    // The toggle is still on
    cy.contains('Enable multi')
      .next()
      .should('have.attr', 'class')
      .and('match', /toggled_on/)
  })

  it('remembers when we disable things', () => {
    // Disable a button
    // We're not using the privacy button because that
    // interacts with analytics libraries, which might
    // not be accessible in a headless environment
    cy.contains('Enable multi')
      .next()
      .click()
    cy.get('button')
      .contains('Continue')
      .click()
    // Leave the settings page
    cy.get("button[class*='navbar__tab__']").contains('FILE')
    // Go back to settings
    cy.get("button[class*='navbar__tab__']")
      .contains('Settings')
      .click()
    // The toggle is still off
    cy.contains('Enable multi')
      .next()
      .should('have.attr', 'class')
      .and('match', /toggled_off/)
  })
})
