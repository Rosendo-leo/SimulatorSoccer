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

public class CreateRobot extends JFrame{
	private JButton add, reset;
	private JLabel tagL, xL, yL, diamL, speedL, iaL, cargoL;
	private JTextField x, y, diam, speed;
	private JCheckBox iaCheck;
	private JComboBox tag, cargo;
	private String tagList[] = {"Azul", "Vermelho"};
	private String cargoList[] = {"Goleiro","Atacante","Auto"};
	
	private Robot robot;
	private String i;
	 
	public CreateRobot(){
		super("Adicionar Robô");
		setPreferredSize(new Dimension(WIDTH,HEIGHT));
		setLayout(new FlowLayout());
		
		tagL = new JLabel("Tag: ");
		add(tagL);
		
		tag = new JComboBox(tagList);
		add(tag);
		
		cargoL = new JLabel("Cargo: ");
		add(cargoL);
		
		cargo = new JComboBox(cargoList);
		add(cargo);
		
		xL = new JLabel("Definir X: ");
		add(xL);
		
		x = new JTextField(12);
		add(x);
		
		yL = new JLabel("Definir Y: ");
		add(yL);
		
		y = new JTextField(12);
		add(y);
		
		diamL = new JLabel("Diâmetro: ");
		add(diamL);
		
		diam = new JTextField(12);
		add(diam);
		
		speedL = new JLabel("Velocidade: ");
		add(speedL);
		
		speed = new JTextField(12);
		add(speed);
	  
		iaCheck = new JCheckBox("IA");
		add(iaCheck);
		
		add = new JButton("Salvar");
		add(add);
		add.addActionListener(new ActionListener() {
		public void actionPerformed(ActionEvent evento){
		    if(evento.getSource() == add) {
		    	if(tag.getSelectedItem() == "Azul") i = "r";
		    	if(tag.getSelectedItem() == "Vermelho") i = "i";
		    	if(tag.getSelectedItem() == "Goleiro") i = "g";
		    	if(tag.getSelectedItem() == "Atacante") i = "a";
		    	if(tag.getSelectedItem() == "Auto") i = "au";
		    	robot = new Robot(Simulator.X(Integer.parseInt(x.getText())),Simulator.Y(Integer.parseInt(y.getText())),Integer.parseInt(diam.getText()),Color.DARK_GRAY,i,Double.parseDouble(speed.getText()),"g");
		    	Simulator.objects.add(robot);
		    	setVisible(false);
			}
		}
		}
		);
	 } 
}
