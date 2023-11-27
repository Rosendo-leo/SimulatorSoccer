package screen;

import java.awt.Color;
import java.awt.Dimension;
import java.awt.FlowLayout;
import java.awt.event.ActionEvent;
import java.awt.event.ActionListener;

import javax.swing.JButton;
import javax.swing.JCheckBox;
import javax.swing.JComboBox;
import javax.swing.JFrame;
import javax.swing.JLabel;
import javax.swing.JTextField;

import main.Simulator;
import object.Robot;

public class Serial extends JFrame{
	private JButton iniciar, cancel;
	private JLabel port, speed;
	private JComboBox portL, speedL;
	private String portList[] = {"COM3", "COM4","COM6"};
	private String speedList[] = {"300","1200","2400","4800","9600","19200","57600","115200","2000000"};
	 
	public Serial(){
		super("Debbug");
		setPreferredSize(new Dimension(WIDTH,HEIGHT));
		setLayout(new FlowLayout());
		
		port = new JLabel("Porta: ");
		add(port);
		
		portL = new JComboBox(portList);
		add(portL);
		
		speed = new JLabel("Taxa: ");
		add(speed);
		
		speedL = new JComboBox(speedList);
		add(speedL);
		
		iniciar = new JButton("Iniciar");
		add(iniciar);
		iniciar.addActionListener(new ActionListener() {
			public void actionPerformed(ActionEvent evento){
			    if(evento.getSource() == iniciar) {
			    
				}
			}
			}
			);
		
		cancel = new JButton("Cancelar");
		add(cancel);
		cancel.addActionListener(new ActionListener() {
			public void actionPerformed(ActionEvent evento){
			    if(evento.getSource() == cancel) {
			    	setVisible(false);
				}
			}
			}
			);
	 } 
}
